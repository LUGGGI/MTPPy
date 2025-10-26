import time
import threading
import logging

from opcua import Client

from mtppy.opcua_server_pea import OPCUAServerPEA
from mtppy.service import Service
from mtppy.procedure import Procedure
from mtppy.parameter_elements import *
from mtppy.indicator_elements import *
from mtppy.active_elements import *

from mtppy.command_codes import CommandCodes
from mtppy.state_codes import StateCodes

CommandCodes = CommandCodes()
StateCodes = StateCodes()

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d; [%(levelname)s]; '
    '%(module)s.%(funcName)s: %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO)
logging.getLogger("opcua").setLevel(logging.ERROR)
logging.getLogger("mtppy.service").setLevel(logging.DEBUG)

_log = logging.getLogger(__name__)

external_event = threading.Event()

###################################################################################################
# Function to wait for two events at the same time
# !!! This modifies the standard threading.Event, could break if it would be changed in the library !!!


def _or_set(self):
    # calls the original set method and then calls the changed callback
    self._set()
    self.changed()


def _or_clear(self):
    # calls the original clear method and then calls the changed callback
    self._clear()
    self.changed()


def _orify(e: threading.Event, changed_callback):
    # save original methods to also be called when set/clear is called
    e._set = e.set
    e._clear = e.clear
    # add changed callback, which is called when the event is set or cleared
    e.changed = changed_callback
    # redefine set and clear methods to call modified methods that also call changed
    e.set = lambda: _or_set(e)
    e.clear = lambda: _or_clear(e)


def OrEvent(*events: threading.Event):
    or_event = threading.Event()

    # check if any of the events are the same
    if len(events) != len(set(events)):
        raise ValueError("Events must be unique.")

    # check if any of the events are already orified
    for e in events:
        if hasattr(e, 'changed'):
            raise ValueError("Events must not be orified already.")

    def changed():
        bools = [e.is_set() for e in events]
        if any(bools):
            or_event.set()
        else:
            or_event.clear()

    # Make every event able to call the changed function
    # when it is set or cleared.
    for e in events:
        _orify(e, changed)
    changed()
    return or_event


def wait_for_either(e1, e2, timeout: float = None) -> bool:
    """
    Waits for either of the two events to be set.
    Args:
        e1 (threading.Event): First event to wait for.
        e2 (threading.Event): Second event to wait for.
        timeout (float): Maximum time to wait in seconds. If None, waits indefinitely.

    Returns:
        bool: True if either event is set, False if timeout occurs.
    """
    return OrEvent(e1, e2).wait(timeout=timeout)
###################################################################################################


class WaitForExternalEvent(Service):
    def __init__(self, tag_name, tag_description):
        super().__init__(tag_name, tag_description)

        # Procedure definition
        proc_1 = Procedure(1, 'default', is_self_completing=True, is_default=True)

        # Adding procedure report value
        proc_1.add_report_value(
            BinView('event_status', v_state_0='no', v_state_1='yes'),
        )

        # Allocating procedure to the service
        self.add_procedure(proc_1)

    def starting(self):
        _log.info('- Starting -')
        _log.info('Creating external event...')

        global external_event
        external_event = threading.Event()

    def execute(self):
        _log.info('- Execute -')

        global external_event

        # This will wait until either the external event is set
        # or the service is requested to stop.
        wait_for_either(external_event, self.get_state_stop_event())

        if external_event.is_set():
            _log.info('External event detected!')
            self.get_current_procedure().report_values['event_status'].set_v(1)
        else:
            _log.info('Service stop requested before external event.')
            self.get_current_procedure().report_values['event_status'].set_v(0)

    def completing(self):
        _log.info('- Completing -')

    # starting, execute, completing methods have to be defined for each service
    # other state methods (see service documentation) can be overridden as needed,
    # by default they only log state entries


if __name__ == '__main__':
    module = OPCUAServerPEA(endpoint="opc.tcp://127.0.0.1:4840/")

    # Service definition
    service = WaitForExternalEvent('WaitForEvent',
                                   'Service that waits for an external event')
    module.add_service(service)

    # Start server
    print('--- Start OPC UA server ---')
    module.run_opcua_server()

    ###############################################################################################
    # Test
    opcua_client = Client(module.endpoint)
    opcua_client.connect()
    time.sleep(1)

    print('--- Set service to Operator mode ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.op_src_mode.StateOpOp').set_value(True)
    time.sleep(1)

    print('--- Start service ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.state_machine.CommandOp').set_value(
        CommandCodes.start)
    time.sleep(4)

    print('--- Trigger external event ---')
    external_event.set()
    time.sleep(2)

    print('--- Reset service ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.state_machine.CommandOp').set_value(
        CommandCodes.reset)
    external_event.clear()
    time.sleep(1)

    print('--- Start service ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.state_machine.CommandOp').set_value(
        CommandCodes.start)
    time.sleep(4)

    print('--- Stop service before external event ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.state_machine.CommandOp').set_value(
        CommandCodes.stop)
    time.sleep(2)

    print('--- Reset service ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.state_machine.CommandOp').set_value(
        CommandCodes.reset)
    time.sleep(1)

    print('--- Set service to Offline mode ---')
    opcua_client.get_node('ns=3;s=services.WaitForEvent.op_src_mode.StateOffOp').set_value(True)
    time.sleep(1)

    print('--- Demo complete ---')
    opcua_client.disconnect()
    module.get_opcua_server().stop()
