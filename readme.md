# MTPPy

## Modular automation

Modular Automation defined in VDI/VDE/NAMUR 2658 offers promising technologies for the process and chemical industry.
It meets the requirements for greater flexibility and a shorter development cycle for production facilities by dividing the process into smaller standardized
units. Key element of Modular Automation is the Module Type Package (MTP).
It represents a standardized and manufacturer-independent description of the automation interface for self-contained production units, or Process Equipment Assemblies
(PEA), and endows the plug-and-produce capability of PEAs.

## Description

The structure of the package mirrors the service interface defined in VDI/VDE/NAMUR 2658 Parts 1, 3, and 4.
Each data assembly has its own class inherited parameters and methods from a higher level class.
The design of the architecture is based on an assumption, that addition of new data assemblies must be possible.

The top level of the application is defined by the class OPCUAServerPEA. This class represents the OPC UA server instance for a single PEA and is responsible for the event-based connection between data assembly’s attributes and the OPC UA server.
This class contains a service set in the form of a dictionary of implemented services as well as a list of indicator, operation and active elements defined on the PEA level.

The class OPCUAServerPEA can also generate the MTP manifest. For this it recursively iterates through the structure of the user-defined service set and adds corresponding entities to the overall MTP structure.
In the end, the method outputs the MTP manifest as an aml file, to be imported into a Process Orchestration Layer software.
Due to open-source paradigm, the MTP manifest can also be extended by other components, e.g. safety relations or energy consumption aspects that currently not defined in the MTP standard.
The class Service represents single services according to VDI/VDE/NAMUR 2658 and provides methods to add configuration parameters and procedures to the service.
Single states of the state machine, e.g. idle, starting, execute, completing, etc., are defined as abstract methods that must be further defined by the user for each concrete service.
The class Service also contains further objects that are responsible for Operation and Source Modes, State Machine and Procedures.
Each of them is implemented as a corresponding class where internal logic according to the standard is defined internally, e.g. transition from Offline mode to Operator mode, CommandEn, state change for states of the state machine.
Procedures as instances of the class Procedure can be added to a service using the corresponding method in the class Service.
The procedure itself is defined by means of related procedure parameters, process value in, process value out, and report values.
The class ProcedureControl serves as a manager for procedures and controls the execution of the selected procedures on the service level.

CommandEnControl is another class defined on the service level as an object of the state machine.
It represents an object to control state changes that can be executed by the state machine.
Each time any command is received from the OPC UA server, a check is made whether the incoming command can be executed from the current state as defined in the VDI/VDE/NAMUR 2658.

Currently only selected data assemblies that are necessarily relevant for soft sensors are implemented.
This includes IndicatorElements (BinView, AnaView, DIntView, and StringView),  OperationElements (BinMan, AnaMan, DIntMan, BinManInt, AnaManInt, DIntManInt) and ActiveElements (AnaVlv, BinVlv, AnaDrv, BinDrv, PIDCtrl), which are defined in Part 4 of VDI/VDE/NAMUR 2658.
Nevertheless, the architecture of the package allows the development of further data assembly classes.

The single states run in separate threads that are managed in the class ThreadControl.
This class makes sure that after each state change the thread that corresponds to the previous state will be naturally terminated, and another thread of the next state started.
Having separate threads allows the running of additional operations, such as data pre-processing or model inference parallel to the main functions of the PEA.
Coupling of data assemblies with OPC UA variables is done by means of event-based subscriptions.
Each OPC UA node that allows changes from the operator or POL via the OPC UA interface creates a subscription object with the corresponding callback method. Each time a change happens, it triggers the callback method with its new value as an input argument.
For example, an incoming command to start the service will run checks first and then execute the corresponding service method named start.\newline
The architecture of MTPPy is depicted in Figure in the res folder in the form of a simplified class diagram.

## Installation

To install the package via pip:

```console
pip3 install mtppy
```

## Development workflow

To develop a PEA using MTPPy, the following workflow is advised.

First, an object of the class OPCUAServerPEA is initialized. The server endpoint and port can be defined in the attribute named endpoint.
Each service must be defined accordingly:

* Configuration parameters are defined and attached to the service.
* At least one procedure must be defined within the service. The procedure might also have internal parameters that need to be also defined and added to the procedure.
* The central task of the developer is to detail the business logic of each state in the service.
  For this, abstract methods of the instantiated Service class objects must be defined.
  Here, service configuration parameters, and procedure parameters can be easily accessed and manipulated.
  For example, in the state starting the required ML model can be imported.
  Further, in the state execute, data are requested, pre-processed, and fed to the prediction function.
  Further, the predicted value is put into a specific report value.
  It is then available for other PEAs or within the process control system.
  Here, the main advantage of MTPPy is clearly visible.
  The developer can seamlessly implement data analytical functionality into services and other types of data assemblies directly in the Python environment without building interfaces to separate components.
* Service must be added to the OPCUAServerPEA instance.
* Elements defined on the PEA level must be also added to the OPCUAServerPEA instance.

After definition of the service set, the MTP file can be generated and the instance of OPCUAServerPEA can be started in one code line.

## Example

More examples can be found the the example folder. Those show:

* minimal virtual PEA
* virtual PEA with recipe
* virtual PEA with pause hold and restart
* virtual PEA with events
* Data Objects

### Service definition

```python
from mtppy.service import Service
from mtppy.procedure import Procedure
from mtppy.parameter_elements import *
from mtppy.indicator_elements import *

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
```

Take into account that the **starting**, **execute** and **completing** states need to be explicitly defined, even if there are no actions. The other states log their entries by default and can be overridden to implement functionality.

States must be implemented in a way that they can react to state changes by checking the `is_state("name_of_state")` function regularly. An event-based system is also possible. For more information, see the corresponding example.

In addition, elements that are service-independent should be defined and added to the PEA.

### PEA definition

Now, the service with its procedure can be added to the PEA instance.

```python
from mtppy.opcua_server_pea import OPCUAServerPEA
from mtppy.active_elements import PIDCtrl

module = OPCUAServerPEA()

# Service definition
service_1 = RandomNumberGenerator('rand_num_gen', 'This services generates random number')
module.add_service(service_1)

# Active element
pid_ctrl = PIDCtrl('pid_ctrl')
module.add_active_element(pid_ctrl)

# Start server
print('--- Start OPC UA server ---')
module.run_opcua_server()
```

The last line will start the OPC UA server.

### MTP generation

To generate an MTP manifest, instantiate an MTP generator.

```python
from mtppy.mtp_generator import MTPGenerator

writer_info_dict = {'WriterName': 'tud/plt', 'WriterID': 'tud/plt', 'WriterVendor': 'tud',
                        'WriterVendorURL': 'www.tud.de',
                        'WriterVersion': '1.0.0',
                        'WriterRelease': '',
                        'LastWritingDateTime': str(datetime.now()),
                        'WriterProjectTitle': 'tu/plt/mtp', 'WriterProjectID': ''}
export_manifest_path = '../manifest_files/example_minimal_manifest.aml'
manifest_template_path = '../manifest_files/manifest_template.xml'
mtp_generator = MTPGenerator(writer_info_dict, export_manifest_path, manifest_template_path)
```

The manifest template can be downloaded here:
https://github.com/p2o-lab/MTPPy/blob/master/manifest_files/manifest_template.xml

and add it as an input argument to the PEA instance.

```python
module = OPCUAServerPEA(mtp_generator)
```
