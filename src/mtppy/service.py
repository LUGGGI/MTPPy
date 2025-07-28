import logging

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
    def __init__(self, tag_name: str, tag_description: str):
        """
        Represents a service of the PEA.

        Args:
            tag_name (str): Tag name of the service.
            tag_description (str): Tag description of the service.
        """
        super().__init__(tag_name, tag_description)

        self.thread_ctrl = ThreadControl(service_name=tag_name)
        self.op_src_mode = OperationSourceMode()

        self.configuration_parameters = {}

        self.procedures = {}
        self.procedure_control = ProcedureControl(self.procedures, self.op_src_mode)

        self.state_machine = StateMachine(operation_source_mode=self.op_src_mode,
                                          procedure_control=self.procedure_control,
                                          execution_routine=self.state_change_callback)

        self.op_src_mode.add_enter_offline_callback(self.state_machine.command_en_ctrl.disable_all)

        self.op_src_mode.add_exit_offline_callback(self.state_machine.command_en_ctrl.set_default)
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
            self.thread_ctrl.reallocate_running_thread()
            return False

    def state_change(self):
        """
        Changes the state.
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

    @abstractmethod
    def idle(self):
        """
        Idle state.
        """
        pass

    @abstractmethod
    def starting(self):
        """
        Starting state.
        """
        pass

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
        pass

    @abstractmethod
    def completed(self):
        """
        Completed state.
        """
        pass

    @abstractmethod
    def pausing(self):
        """
        Pausing state.
        """
        pass

    @abstractmethod
    def paused(self):
        """
        Paused state.
        """
        pass

    @abstractmethod
    def resuming(self):
        """
        Resuming state.
        """
        pass

    @abstractmethod
    def holding(self):
        """
        Holding state.
        """
        pass

    @abstractmethod
    def held(self):
        """
        Held state.
        """
        pass

    @abstractmethod
    def unholding(self):
        """
        Unholding state.
        """
        pass

    @abstractmethod
    def stopping(self):
        """
        Stopping state.
        """
        pass

    @abstractmethod
    def stopped(self):
        """
        Stopped state.
        """
        pass

    @abstractmethod
    def aborting(self):
        """
        Aborting state.
        """
        pass

    @abstractmethod
    def aborted(self):
        """
        Aborted state.
        """
        pass

    @abstractmethod
    def resetting(self):
        """
        Resetting state.
        """
        pass
