from opcua import Client

from mtppy.opcua_server_pea import OPCUAServerPEA

from mtppy.indicator_elements import *
from mtppy.operation_elements import *
from mtppy.active_elements import *
from mtppy.suc_data_assembly import SUCDataAssembly
from mtppy.attribute import Attribute

import time

logging.basicConfig(
    format='%(asctime)s.%(msecs)03d; [%(levelname)s]; '
    '%(module)s.%(funcName)s: %(message)s',
    datefmt='%H:%M:%S', level=logging.INFO)
logging.getLogger("opcua").setLevel(logging.ERROR)
logging.getLogger("mtppy.indicator_elements").setLevel(logging.DEBUG)
logging.getLogger("mtppy.operation_elements").setLevel(logging.DEBUG)
logging.getLogger("mtppy.active_elements").setLevel(logging.DEBUG)

_log = logging.getLogger(__name__)


module = OPCUAServerPEA(endpoint="opc.tcp://127.0.0.1:4840/")

### Indicator elements ###
bin_view = BinView('indicator_bin', 'demo object', v_state_0='Off', v_state_1='On')
dint_view = DIntView('indicator_dint', 'demo object', v_scl_min=0, v_scl_max=100, v_unit=1342)
ana_view = AnaView('indicator_ana', 'demo object', v_scl_min=0, v_scl_max=100, v_unit=1342)
str_view = StringView('indicator_str', 'demo object')

# add indicator elements to the module
module.add_indicator_element(bin_view)
module.add_indicator_element(dint_view)
module.add_indicator_element(ana_view)
module.add_indicator_element(str_view)


### Operation elements ###
bin_man = BinMan('op_bin', 'demo object', v_state_0='Off', v_state_1='On', init_value=0)
dint_man = DIntMan('op_dint', 'demo object', v_min=0, v_max=100,
                   v_scl_min=0, v_scl_max=100, v_unit=1342, init_value=0)
ana_man = AnaMan('op_ana', 'demo object', v_min=0, v_max=100,
                 v_scl_min=0, v_scl_max=100, v_unit=1342, init_value=0)

# add operation elements to the module
module.add_operation_element(bin_man)
module.add_operation_element(dint_man)
module.add_operation_element(ana_man)


## Internal operation elements ##
bin_man_int = BinManInt('op_bin_int', 'demo object', v_state_0='Off', v_state_1='On', init_value=0)
dint_man_int = DIntManInt('op_dint_int', 'demo object', v_min=0, v_max=100,
                          v_scl_min=0, v_scl_max=100, v_unit=1342, init_value=0)
ana_man_int = AnaManInt('op_ana_int', 'demo object', v_min=0, v_max=100,
                        v_scl_min=0, v_scl_max=100, v_unit=1342, init_value=0)

# add internal operation elements to the module
module.add_operation_element(bin_man_int)
module.add_operation_element(dint_man_int)
module.add_operation_element(ana_man_int)


### Active elements ###
bin_vlv = BinVlv('active_bin', 'demo object', safe_pos=0, safe_pos_en=True,
                 perm_en=True, intl_en=True, prot_en=True)

# add active elements to the module
module.add_active_element(bin_vlv)


### Custom Data Assembly ###
# it is also possible to create custom data assemblies by inheriting from SUCDataAssembly
# Attributes can be using the self._add_attribute() function inside the __init__ function
class CustomDataAssembly(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str = '', pol_request: int = 0):
        super().__init__(tag_name, tag_description)

        self._add_attribute(Attribute('POLRequest', int,
                            init_value=pol_request, sub_cb=self._set_pol_request))
        self._add_attribute(Attribute('PEAResponse', str, init_value='Hello World'))

        self.pol_request = pol_request

    def set_pea_response(self, value: str):
        self.attributes['PEAResponse'].set_value(value)
        _log.info(f'PEAResponse set to {value}')

    def get_pol_request(self) -> int:
        return self.pol_request

    def _set_pol_request(self, value: int):
        # ignore reset callback
        if value == 0:
            return
        self.pol_request = value
        _log.info(f'POLRequest set to {value} ')

        if value == 42:
            self.set_pea_response('The answer to life, the universe and everything.')
        else:
            self.set_pea_response(f'POLRequest was {value}.')

        self.attributes['POLRequest'].set_value(0)  # reset POLRequest after reading


custom_da = CustomDataAssembly('custom_da_1', 'demo object', pol_request=123)
module.add_custom_data_assembly(custom_da, "custom_data_assemblies")

# start the OPC UA server
module.run_opcua_server()

# while True:
#     time.sleep(1)

###############################################################################################
# Test
opcua_client = Client(module.endpoint)
opcua_client.connect()
time.sleep(1)


print('--- Set values of indicator elements ---')
bin_view.set_v(1)
dint_view.set_v(55)
ana_view.set_v(33.3)
str_view.set_v('Hello MTPPy!')
time.sleep(1)

print('--- Print values of indicator elements (Simulating HMI side) ---')
print(f"bin_view: {opcua_client.get_node('ns=3;s=indicator_elements.indicator_bin.V').get_value()}")
print(f"dint_view: {opcua_client.get_node('ns=3;s=indicator_elements.indicator_dint.V').get_value()}")
print(f"ana_view: {opcua_client.get_node('ns=3;s=indicator_elements.indicator_ana.V').get_value()}")
print(f"str_view: {opcua_client.get_node('ns=3;s=indicator_elements.indicator_str.V').get_value()}")
time.sleep(2)


print()
print('--- Set values of operation elements (Simulating HMI side) ---')
opcua_client.get_node('ns=3;s=operation_elements.op_bin.VMan').set_value(1)
opcua_client.get_node('ns=3;s=operation_elements.op_dint.VMan').set_value(77)
opcua_client.get_node('ns=3;s=operation_elements.op_ana.VMan').set_value(44.4)
time.sleep(1)

print('--- Print values of operation elements ---')
print(f"bin_man: {bin_man.get_v_out()}")
print(f"dint_man: {dint_man.get_v_out()}")
print(f"ana_man: {ana_man.get_v_out()}")
time.sleep(2)


print()
print('--- Set values of internal operation elements ---')
bin_man_int.set_v_int(1)
dint_man_int.set_v_int(88)
ana_man_int.set_v_int(55.5)
time.sleep(1)

print('--- Print values of internal operation elements ---')
print(
    f"bin_man_int: {opcua_client.get_node('ns=3;s=operation_elements.op_bin_int.VOut').get_value()}")
print(
    f"dint_man_int: {opcua_client.get_node('ns=3;s=operation_elements.op_dint_int.VOut').get_value()}")
print(
    f"ana_man_int: {opcua_client.get_node('ns=3;s=operation_elements.op_ana_int.VOut').get_value()}")
time.sleep(2)

print('--- Set SrcChannel to 0 (operator switches)')
opcua_client.get_node(
    'ns=3;s=operation_elements.op_bin_int.op_src_mode.SrcChannel').set_value(False)
print('--- Set to Manual via operator ---')
opcua_client.get_node('ns=3;s=operation_elements.op_bin_int.op_src_mode.SrcManOp').set_value(True)
print('--- Set value via operator ---')
opcua_client.get_node('ns=3;s=operation_elements.op_bin_int.VMan').set_value(0)
time.sleep(1)
print(f"bin_man_int: {bin_man_int.get_v_out()}")
time.sleep(1)

print('--- Set SrcChannel to 1 (internal control) ---')
opcua_client.get_node(
    'ns=3;s=operation_elements.op_bin_int.op_src_mode.SrcChannel').set_value(True)
print('--- Set to Automatic via internal control ---')
opcua_client.get_node('ns=3;s=operation_elements.op_bin_int.op_src_mode.SrcIntAut').set_value(True)
print('--- Set value via internal control ---')
bin_man_int.set_v_int(1)
time.sleep(1)
print(
    f"bin_man_int: {opcua_client.get_node('ns=3;s=operation_elements.op_bin_int.VOut').get_value()}")
time.sleep(2)


print()
print('--- Set values of active element ---')
bin_vlv.set_open_aut(True)
time.sleep(1)
print(
    f"bin_vlv position: {opcua_client.get_node('ns=3;s=active_elements.active_bin.Ctrl').get_value()}")
time.sleep(1)
bin_vlv.set_close_aut(True)
time.sleep(1)
print(
    f"bin_vlv position: {opcua_client.get_node('ns=3;s=active_elements.active_bin.Ctrl').get_value()}")
time.sleep(2)

print('--- Demonstrate bin_vlv locks ---')
locks = bin_vlv.locks

print(f"Initial permit status: {locks.permit_status()}")
print(f"Initial interlock status: {locks.interlock_status()}")
print(f"Initial protect status: {locks.protect_status()}")

# Enable and disable permit
locks.set_permit(False)
print(f"Permit status after disabling: {locks.permit_status()}")
bin_vlv.set_open_aut(True)
time.sleep(1)
print(
    f"bin_vlv position (should not change): {opcua_client.get_node('ns=3;s=active_elements.active_bin.Ctrl').get_value()}")
time.sleep(1)
locks.set_permit(True)
print(f"Permit status after enabling: {locks.permit_status()}")
time.sleep(1)
bin_vlv.set_open_aut(True)
time.sleep(1)
print(
    f"bin_vlv position (should change now): {opcua_client.get_node('ns=3;s=active_elements.active_bin.Ctrl').get_value()}")
time.sleep(2)

# Enable and disable interlock
locks.set_interlock(True)
print(f"Interlock status after enabling: {locks.interlock_status()}")
sleep(1)
print(f"Interlock triggered, valve should close automatically: valve status: {bin_vlv.get_ctrl()}")
locks.set_interlock(False)
print(f"Interlock status after disabling: {locks.interlock_status()}")

# Enable and disable protect
locks.set_protect(True)
print(f"Protect status after enabling: {locks.protect_status()}")
bin_vlv.reset_vlv()
print(f"Protect status after disabling: {locks.protect_status()}")
time.sleep(2)


print()
print('--- Set and read Custom Data Assembly attributes ---')
print("--- Set POLRequest to 42 (Simulating HMI side) ---")
opcua_client.get_node('ns=3;s=custom_data_assemblies.custom_da_1.POLRequest').set_value(42)
time.sleep(1)
print("--- Read POLRequest and PEAResponse attributes ---")
print(f"POLRequest: {custom_da.get_pol_request()}")
print(
    f"PEAResponse: {opcua_client.get_node('ns=3;s=custom_data_assemblies.custom_da_1.PEAResponse').get_value()}")
time.sleep(1)
print("--- Try setting the PEAResponse attribute from HMI side (should have no effect) ---")
try:
    opcua_client.get_node('ns=3;s=custom_data_assemblies.custom_da_1.PEAResponse').set_value(
        'PEAResponse set from from HMI')
except Exception as e:
    print(f"Caught exception as expected: {e}")
time.sleep(1)
print(
    f"PEAResponse on server (should not be changed): {opcua_client.get_node('ns=3;s=custom_data_assemblies.custom_da_1.PEAResponse').get_value()}")
time.sleep(2)

print('--- Demo complete ---')
opcua_client.disconnect()
module.get_opcua_server().stop()
