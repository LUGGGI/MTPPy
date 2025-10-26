import time
import random
from datetime import datetime
import logging

from opcua import Client

from mtppy.opcua_server_pea import OPCUAServerPEA
from mtppy.mtp_generator import MTPGenerator
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
    format='%(asctime)s.%(msecs)03d; [%(levelname)s];'
    '%(module)s.%(funcName)s: %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO)
logging.getLogger("opcua").setLevel(logging.ERROR)
logging.getLogger("mtppy.service").setLevel(logging.DEBUG)

_log = logging.getLogger(__name__)


class RandomNumberGenerator(Service):
    def __init__(self, tag_name, tag_description):
        super().__init__(tag_name, tag_description)

        # Procedure definition
        proc_1 = Procedure(1, 'cont', is_self_completing=False, is_default=True)

        # Adding two procedure parameters
        proc_1.add_procedure_parameter(
            DIntServParam('lower_bound', v_min=0, v_max=100, v_scl_min=0, v_scl_max=100, v_unit=23))
        proc_1.add_procedure_parameter(
            DIntServParam('upper_bound', v_min=0, v_max=100, v_scl_min=0, v_scl_max=100, v_unit=23))

        # optional: link op_src_mode of procedure parameters to service op_src_mode
        for parameter in proc_1.procedure_parameters.values():
            self.op_src_mode.add_linked_op_src_mode(parameter.op_src_mode)

        # Adding procedure report value
        proc_1.add_report_value(
            AnaView('generated_value', v_scl_min=0, v_scl_max=100, v_unit=23),
        )

        # Allocating procedure to the service
        self.add_procedure(proc_1)

    def starting(self):
        _log.info('- Starting -')
        _log.info('Applying procedure parameters...')

    def execute(self):
        _log.info('- Execute -')
        cycle = 0
        while self.is_state('execute'):
            _log.info('Execute cycle %i' % cycle)

            # Read procedure parameters
            lower_bound = self.procedures[1].procedure_parameters['lower_bound'].get_v_out()
            upper_bound = self.procedures[1].procedure_parameters['upper_bound'].get_v_out()

            # Execute random number generation
            generated_number = random.randint(lower_bound, upper_bound)

            # Return report value
            self.procedures[1].report_values['generated_value'].set_v(generated_number)

            cycle += 1
            time.sleep(0.1)

    def completing(self):
        _log.info('- Completing -')

    # starting, execute, completing methods have to be defined for each service
    # other state methods (see service documentation) can be overridden as needed,
    # by default they only log state entries


if __name__ == '__main__':

    writer_info_dict = {'WriterName': 'tud/plt', 'WriterID': 'tud/plt', 'WriterVendor': 'tud',
                        'WriterVendorURL': 'www.tud.de',
                        'WriterVersion': '1.0.0', 'WriterRelease': '', 'LastWritingDateTime': str(datetime.now()),
                        'WriterProjectTitle': 'tu/plt/mtp', 'WriterProjectID': ''}
    export_manifest_path = '../manifest_files/example_minimal_manifest.aml'
    manifest_template_path = '../manifest_files/manifest_template.xml'
    mtp_generator = MTPGenerator(writer_info_dict, export_manifest_path, manifest_template_path)

    module = OPCUAServerPEA(mtp_generator, endpoint="opc.tcp://127.0.0.1:4840/")

    # Service definition
    service_1 = RandomNumberGenerator('rand_num_gen', 'This services generates random number')
    module.add_service(service_1)

    # Active element
    pid_ctrl = PIDCtrl('pid_ctrl')
    module.add_active_element(pid_ctrl)

    # Start server
    print('--- Start OPC UA server ---')
    module.run_opcua_server()

    ###############################################################################################
    # Test
    opcua_client = Client(module.endpoint)
    opcua_client.connect()
    time.sleep(1)

    print('--- Set procedure parameters to Operator mode ---')
    opcua_client.get_node(
        'ns=3;s=services.rand_num_gen.procedures.cont.procedure_parameters.lower_bound.op_src_mode.StateOpOp').set_value(True)
    opcua_client.get_node(
        'ns=3;s=services.rand_num_gen.procedures.cont.procedure_parameters.upper_bound.op_src_mode.StateOpOp').set_value(True)
    time.sleep(1)

    print('--- Set procedure parameter values ---')
    opcua_client.get_node(
        'ns=3;s=services.rand_num_gen.procedures.cont.procedure_parameters.lower_bound.VOp').set_value(40)
    opcua_client.get_node(
        'ns=3;s=services.rand_num_gen.procedures.cont.procedure_parameters.upper_bound.VOp').set_value(60)
    time.sleep(1)

    print('--- Set service to Operator mode ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.op_src_mode.StateOpOp').set_value(True)
    time.sleep(1)

    print('--- Start service ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
        CommandCodes.start)
    time.sleep(10)

    print('--- Complete service ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
        CommandCodes.complete)
    time.sleep(1)

    print('--- Reset service ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.state_machine.CommandOp').set_value(
        CommandCodes.reset)
    time.sleep(1)

    print('--- Set service to Offline mode ---')
    opcua_client.get_node('ns=3;s=services.rand_num_gen.op_src_mode.StateOffOp').set_value(True)
    time.sleep(1)

    print('--- Demo complete ---')
    opcua_client.disconnect()
    module.get_opcua_server().stop()
