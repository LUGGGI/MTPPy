import time
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


class Counter(Service):
    def __init__(self, tag_name, tag_description):
        super().__init__(tag_name, tag_description)

        # Procedure definition
        proc_1 = Procedure(1, 'cont', is_self_completing=True, is_default=True)

        # Adding procedure report value
        proc_1.add_report_value(
            DIntView('count', v_scl_min=0, v_scl_max=100, v_unit=23),
        )

        # Allocating procedure to the service
        self.add_procedure(proc_1)

        # Enable pause and hold functionality
        self.enable_pause_loop()
        self.enable_hold_loop()

        # Enable reset functionality
        # self.enable_restart()

        # add count variable
        self.count = 0

    def starting(self):
        _log.info('- Starting -')
        self.count = 0
        self.get_current_procedure().report_values['count'].set_v(self.count)
        # time.sleep(1)

    def execute(self):
        _log.info('- Execute -')
        start_time = int(time.time() % 100)
        # state_stop_event = self.get_state_stop_event()
        # _log.info(f"State stop event: {state_stop_event.is_set()} for start at {start_time}")

        while self.is_state("execute") and self.count < 100:

            # Execute counting
            self.count += 1
            self.get_current_procedure().report_values['count'].set_v(self.count)
            _log.info(f'Count value: {self.count:3d} start at {start_time}')

            time.sleep(0.1)

    def completing(self):
        _log.info('- Completing -')

        _log.info(f'Final count value: {self.count}')

    # starting, execute, completing methods have to be defined for each service

    # if enabled at least one of the pausing/ holding functions should be implemented
    def pausing(self):
        _log.info(f'Count value at pausing: {self.count}')

    def paused(self):
        _log.info(f"Count value at paused: {self.count}")

    def resuming(self):
        return super().resuming()

    def holding(self):
        _log.info(f"Count value at holding: {self.count}")

    def hold(self):
        _log.info(f'Count value at hold: {self.count}')

    def unholding(self):
        return super().unholding()

    def restarting(self):
        _log.info('- Restarting -')

        _log.info("Resetting count value")
    # other state methods (see service documentation) can be overridden as needed,
    # by default they only log state entries


if __name__ == '__main__':

    module = OPCUAServerPEA(endpoint="opc.tcp://127.0.0.1:4840/")

    # Service definition
    service_1 = Counter('counter', 'Counts from 0 to 100')
    module.add_service(service_1)

    # Start server
    print('--- Start OPC UA server ---')
    module.run_opcua_server()

    ###############################################################################################
    # Test
    opcua_client = Client(module.endpoint)
    opcua_client.connect()
    time.sleep(1)

    print('--- Set service to Operator mode ---')
    opcua_client.get_node('ns=3;s=services.counter.op_src_mode.StateOpOp').set_value(True)
    time.sleep(1)

    print('--- Start service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.start)
    time.sleep(4)

    print('--- Restart service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.restart)
    time.sleep(4)

    print('--- Pause service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.pause)
    time.sleep(2)

    print('--- Resume service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.resume)
    time.sleep(4)

    print('--- Hold service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.hold)
    time.sleep(2)

    print('--- Unhold service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.unhold)

    print('--- Waiting until service completes ---')
    while opcua_client.get_node('ns=3;s=services.counter.state_machine.StateCur').get_value() != StateCodes.completed:
        time.sleep(1)

    print('--- Reset service ---')
    opcua_client.get_node('ns=3;s=services.counter.state_machine.CommandOp').set_value(
        CommandCodes.reset)
    time.sleep(1)

    print('--- Set service to Offline mode ---')
    opcua_client.get_node('ns=3;s=services.counter.op_src_mode.StateOffOp').set_value(True)
    time.sleep(1)

    print('--- Demo complete ---')
    opcua_client.disconnect()
    module.get_opcua_server().stop()
