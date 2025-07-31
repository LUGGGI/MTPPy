import logging
import time
from threading import Event

from abc import abstractmethod

from MTPPy_Async.src.mtppy.suc_data_assembly import SUCServiceControl
from MTPPy_Async.src.mtppy.thread_control import ThreadControl
from MTPPy_Async.src.mtppy.operation_source_mode import OperationSourceMode
from MTPPy_Async.src.mtppy.state_machine import StateMachine
from MTPPy_Async.src.mtppy.procedure_control import ProcedureControl
from MTPPy_Async.src.mtppy.state_codes import StateCodes
from MTPPy_Async.src.mtppy.procedure import Procedure
from MTPPy_Async.src.mtppy.suc_data_assembly import SUCOperationElement

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")

StateCodes = StateCodes()


class Service(SUCServiceControl):
    """Represents a service of the PEA.

    To create a new service, inherit from this class and implement at least the abstract methods. 
    These include:
    - starting
    - execute
    - completing

    Other methods can be overridden as needed. 
    By default the higher level methods (on the right side) will call the lower level methods.  
    See the following diagram for how the methods are called:

    +------------+      +------------+      +------------+      +------------+      +------------+
    | completing |  <-  |  pausing   |  <-  |  holding   |  <-  |  stopping  |  <-  |  aborting  |
    +------------+      +------------+      +------------+      +------------+      +------------+
                        +------------+      +------------+      +------------+      +------------+
                    ||  |   paused   |  <-  |    held    |  <-  |  stopped   |  <-  |  aborted   |
                        +------------+      +------------+      +------------+      +------------+
    +------------+      +------------+      +------------+      
    |  starting  |  <-  |  resuming  |  <-  | unholding  |      
    +------------+      +------------+      +------------+   

    """

    def __init__(self, tag_name: str, tag_description: str):
        """
        Represents a service of the PEA.

        Args:
            tag_name (str): Tag name of the service.
            tag_description (str): Tag description of the service.
        """
        super().__init__(tag_name, tag_description)

        self.op_src_mode = OperationSourceMode()

        self.configuration_parameters = {}

        self.procedures = {}
        self.procedure_control = ProcedureControl(self.procedures, self.op_src_mode)

        self.state_machine = StateMachine(operation_source_mode=self.op_src_mode,
                                          procedure_control=self.procedure_control,
                                          execution_routine=self.state_change_callback)

        self.thread_ctrl = ThreadControl(service_name=tag_name,
                                         state_change_function=self.state_change())

        self.op_src_mode.add_enter_offline_callback(self.state_machine.command_en_ctrl.disable_all)
        self.op_src_mode.add_enter_offline_callback(self.thread_ctrl.stop_thread)

        self.op_src_mode.add_exit_offline_callback(self.state_machine.command_en_ctrl.set_default)
        self.op_src_mode.add_exit_offline_callback(self.state_machine.update_command_en)
        self.op_src_mode.add_exit_offline_callback(self.apply_configuration_parameters)
        self.op_src_mode.add_exit_offline_callback(self.init_idle_state)

    def init_idle_state(self):
        """
        Initializes the idle state.
        """
        self.state_change_callback()

    def state_change_callback(self):
        """
        Callback for state changes.
        """
        if self.op_src_mode.attributes['StateOffAct'].value:
            return

        state_str = self.state_machine.get_current_state_str()
        function_to_execute = eval(f'self.{state_str}')
        self.thread_ctrl.request_state(state_str, function_to_execute)
        self.thread_ctrl.reallocate_running_thread()
        if state_str == 'idle':
            self.op_src_mode.allow_switch_to_offline_mode(True)
        else:
            self.op_src_mode.allow_switch_to_offline_mode(False)

    def is_state(self, state_str):
        """
        Checks if the current state matches the given state.

        Args:
            state_str (str): State to check.

        Returns:
            bool: True if the current state matches, False otherwise.
        """
        if state_str is self.state_machine.get_current_state_str():
            return True
        else:
            # start the next thread if the state is not the current one
            self.thread_ctrl.reallocate_running_thread()
            return False

    def get_state_stop_event(self) -> Event:
        """
        Returns an event that is set when the state should stop.

        Returns:
            Event: Event that is set when the state should stop.
        """
        if self.thread_ctrl.thread is None:
            raise RuntimeError("Thread is not running.")

        return self.thread_ctrl.thread.stop_event

    def state_change(self):
        """
        Changes the state. Has to be called by each transitional state method.
        """
        self.state_machine.state_change()

    def add_configuration_parameter(self, configuration_parameter: SUCOperationElement):
        """
        Adds a configuration parameter to the service.

        Args:
            configuration_parameter (SUCOperationElement): Configuration parameter to add.
        """
        self.configuration_parameters[configuration_parameter.tag_name] = configuration_parameter

    def apply_configuration_parameters(self):
        """
        Applies configuration parameters.
        """
        _logger.debug('Applying service configuration parameters')
        for configuration_parameter in self.configuration_parameters.values():
            configuration_parameter.set_v_out()

    def add_procedure(self, procedure: Procedure):
        """
        Adds a procedure to the service.

        Args:
            procedure (Procedure): Procedure to add.
        """
        self.procedures[procedure.attributes['ProcedureId'].value] = procedure
        if procedure.attributes['IsDefault'].value:
            self.procedure_control.default_procedure_id = procedure.attributes['ProcedureId'].value
            self.procedure_control.attributes['ProcedureOp'].init_value = self.procedure_control.default_procedure_id
            self.procedure_control.attributes['ProcedureInt'].init_value = self.procedure_control.default_procedure_id
            self.procedure_control.attributes['ProcedureExt'].init_value = self.procedure_control.default_procedure_id

    def idle(self):
        """
        Idle state.
        """
        _logger.debug(f"{self.tag_name} - Idle -")
        cycle = 0
        while self.is_state("idle") and not self.thread_ctrl.thread.stop_event.is_set():
            _logger.debug(f"{self.tag_name} - Idle cycle {cycle}")
            cycle += 1
            time.sleep(3)

    @abstractmethod
    def starting(self):
        """
        Starting state.
        """
        self.state_change()

    @abstractmethod
    def execute(self):
        """
        Execute state.
        """
        pass

    @abstractmethod
    def completing(self):
        """
        Completing state.
        """
        self.state_change()

    def completed(self):
        """
        Completed state.
        """
        if self.state_machine.get_current_state_str() == "completed":
            _logger.debug(f"{self.tag_name} - Completed -")
        else:
            pass

    def pausing(self):
        """
        Pausing state. If not overridden, it will call the completing method.
        """
        if self.state_machine.get_current_state_str() == "pausing":
            _logger.debug(f"{self.tag_name} - Pausing -")
        else:
            pass
        # call the completing method to also execute the logic for the completing state
        self.completing()

    def paused(self):
        """
        Paused state.
        """
        if self.state_machine.get_current_state_str() == "paused":
            _logger.debug(f"{self.tag_name} - Paused -")
        else:
            pass

    def resuming(self):
        """
        Resuming state. If not overridden, it will call the starting method.
        """
        if self.state_machine.get_current_state_str() == "resuming":
            _logger.debug(f"{self.tag_name} - Resuming -")
        else:
            pass
        # call the starting method to also execute the logic for the starting state
        self.starting()

    def holding(self):
        """
        Holding state. If not overridden, it will call the pausing method.
        """
        if self.state_machine.get_current_state_str() == "holding":
            _logger.debug(f"{self.tag_name} - Holding -")
        else:
            pass
        # call the pausing method to also execute the logic for the pausing state
        self.pausing()

    def held(self):
        """
        Held state. If not overridden, it will call the paused method.
        """
        if self.state_machine.get_current_state_str() == "held":
            _logger.debug(f"{self.tag_name} - Held -")
        else:
            pass
        # call the paused method to also execute the logic for the paused state
        self.paused()

    def unholding(self):
        """
        Unholding state. If not overridden, it will call the resuming method.
        """
        if self.state_machine.get_current_state_str() == "unholding":
            _logger.debug(f"{self.tag_name} - Unholding -")
        else:
            pass
        # call the resuming method to also execute the logic for the resuming state
        self.resuming()

    def stopping(self):
        """
        Stopping state. If not overridden, it will call the holding method.
        """
        if self.state_machine.get_current_state_str() == "stopping":
            _logger.debug(f"{self.tag_name} - Stopping -")
        else:
            pass
        # call the holding method to also execute the logic for the holding state
        self.holding()

    def stopped(self):
        """
        Stopped state. If not overridden, it will call the held method.
        """
        if self.state_machine.get_current_state_str() == "stopped":
            _logger.debug(f"{self.tag_name} - Stopped -")
        else:
            pass
        # call the held method to also execute the logic for the held state
        self.held()

    def aborting(self):
        """
        Aborting state. If not overridden, it will call the stopping method.
        """
        if self.state_machine.get_current_state_str() == "aborting":
            _logger.debug(f"{self.tag_name} - Aborting -")
        else:
            pass
        # call the stopping method to also execute the logic for the stopping state
        self.stopping()

    def aborted(self):
        """
        Aborted state. If not overridden, it will call the stopped method.
        """
        if self.state_machine.get_current_state_str() == "aborted":
            _logger.debug(f"{self.tag_name} - Aborted -")
        else:
            pass
        # call the stopped method to also execute the logic for the stopped state
        self.stopped()

    def resetting(self):
        """
        Resetting state.
        """
        if self.state_machine.get_current_state_str() == "resetting":
            _logger.debug(f"{self.tag_name} - Resetting -")
        else:
            pass
        # Reset the state machine to idle
        self.thread_ctrl.exception = None
        self.state_change()
