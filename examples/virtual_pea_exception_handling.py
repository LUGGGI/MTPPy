import time
import random
import logging

from opcua import Client

from mtppy.opcua_server_pea import OPCUAServerPEA
from mtppy.service import Service
from mtppy.procedure import Procedure
from mtppy.indicator_elements import *

from mtppy.command_codes import CommandCodes
from mtppy.state_codes import StateCodes

CommandCodes = CommandCodes()
StateCodes = StateCodes()

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d; [%(levelname)s];'
    '%(module)s.%(funcName)s: %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO)
logging.getLogger("opcua").setLevel(logging.ERROR)
logging.getLogger("mtppy.service").setLevel(logging.DEBUG)

_log = logging.getLogger(__name__)


class ErrorException(Exception):
    pass


class WarningException(Exception):
    pass


class RandomNumberGenerator(Service):
    def __init__(self, tag_name, tag_description):
        super().__init__(tag_name, tag_description, self.exception_callback)

        # Procedure definition
        proc_1 = Procedure(1, 'default', is_self_completing=False, is_default=True)

        # Adding procedure report value
        proc_1.add_report_value(
            AnaView('generated_value', v_scl_min=0, v_scl_max=100, v_unit=23),
        )

        # Allocating procedure to the service
        self.add_procedure(proc_1)

        self.enable_hold_loop()

        self.cycle_count = 0

    def starting(self):
        _log.info('- Starting -')
        _log.info('Applying procedure parameters...')
        self.cycle_count = 0

    def execute(self):
        _log.info('- Execute -')
        lower_bound = 0
        upper_bound = 10
        while self.is_state('execute'):
            _log.info(f'Execute cycle {self.cycle_count}')

            # Execute random number generation
            generated_number = random.randint(lower_bound, upper_bound)

            # Return report value
            self.procedures[1].report_values['generated_value'].set_v(generated_number)
            if generated_number == 5:
                raise WarningException('This is a warning exception for testing.')
            if generated_number == 8:
                raise ErrorException('This is an error exception for testing.')
            self.cycle_count += 1
            time.sleep(0.1)

    def completing(self):
        _log.info('- Completing -')

    def exception_callback(self, exception: Exception):
        if isinstance(exception, WarningException):
            _log.warning(f'Warning exception handled in exception_callback: {str(exception)}')
            # handle warning exception (e.g., set service to hold state)
            self.state_machine.hold()
        elif isinstance(exception, ErrorException):
            _log.error(f'Error exception handled in exception_callback: {str(exception)}')
            # handle error exception (e.g., set service to aborted state)
            self.state_machine.abort()
        else:
            _log.error(f'Unknown exception handled in exception_callback: {str(exception)}')
            self.state_machine.abort()

    # starting, execute, completing methods have to be defined for each service
    # other state methods (see service documentation) can be overridden as needed,
    # by default they only log state entries


if __name__ == '__main__':

    module = OPCUAServerPEA()

    # Service definition
    service_1 = RandomNumberGenerator('rand_num_gen', 'This services generates random number')
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
    opcua_client.get_node('ns=3;s=services.rand_num_gen.op_src_mode.StateOpOp').set_value(True)
    time.sleep(1)

    print('--- Start service ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
        CommandCodes.start)

    cycle = 0
    while cycle < 12:
        if opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.StateCur').get_value() == StateCodes.held:
            print(f'--- Unholding service at cycle ---')
            opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
                CommandCodes.unhold)
        if opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.StateCur').get_value() == StateCodes.aborted:
            print(f'--- Resetting service at cycle ---')
            opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
                CommandCodes.reset)
            break

        time.sleep(1)
        cycle += 1

    if cycle >= 12:
        print('--- Complete service ---')
        opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
            CommandCodes.complete)
        time.sleep(1)

        print('--- Reset service ---')
        opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
            CommandCodes.reset)
        time.sleep(1)

    time.sleep(1)
    print('--- Set service to Offline mode ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.op_src_mode.StateOffOp').set_value(True)
    time.sleep(1)

    print('--- Demo complete ---')
    opcua_client.disconnect()
    module.get_opcua_server().stop()
