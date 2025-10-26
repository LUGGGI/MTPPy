import logging
import time
from threading import Event
from collections.abc import Callable

from abc import abstractmethod

from mtppy.suc_data_assembly import SUCServiceControl
from mtppy.thread_control import ThreadControl, StoppableThread
from mtppy.operation_source_mode import OperationSourceMode
from mtppy.state_machine import StateMachine
from mtppy.procedure_control import ProcedureControl
from mtppy.procedure import Procedure
from mtppy.suc_data_assembly import SUCParameterElement

_logger = logging.getLogger(__name__)


class Service(SUCServiceControl):
    """Represents a service of the PEA.

    To create a new service, inherit from this class and implement at least the abstract methods.
    These include:
    - starting
    - execute
    - completing

    Additionally, you may override other state methods to implement specific behavior for 
    those states. Those include:
    - completed
    - stopping
    - stopped
    - aborting
    - aborted
    - resetting

    Some states are part of control loops that can be enabled or disabled. These states include:
    - pause_loop
        - pausing
        - paused
        - resuming
    - hold_loop
        - holding
        - held
        - unholding

    Methods ending with "ing" are transitional states. After running once they will automatically
    transition to the next state.  
    If a function runs in a loop, it must check for the current state using `is_state(state_str)`
    or it must check for the stop event using `get_state_stop_event()`. Because those indicate 
    that a state transition has been requested and the function must return.
    """

    def __init__(self, tag_name: str, tag_description: str, exception_callback: Callable[[Exception], None] = None):
        """
        Represents a service of the PEA.

        Args:
            tag_name (str): Tag name of the service.
            tag_description (str): Tag description of the service.
            exception_callback (Callable[[Exception], None]): Function to call
                when an exception occurs in the thread. If None just logs the exception.
        """
        super().__init__(tag_name, tag_description)
        self.exception = None

        self.op_src_mode = OperationSourceMode(tag_name)

        self.configuration_parameters = {}

        self.procedures: dict[int, Procedure] = {}
        self.procedure_control = ProcedureControl(self.procedures, self.op_src_mode)

        self.state_machine = StateMachine(operation_source_mode=self.op_src_mode,
                                          procedure_control=self.procedure_control,
                                          execution_routine=self._state_change_callback)

        self.thread_ctrl = ThreadControl(service_name=tag_name,
                                         state_change_function=self._state_change,
                                         exception_callback=exception_callback)

        self.op_src_mode.add_enter_offline_callback(self.state_machine.command_en_ctrl.disable_all)
        self.op_src_mode.add_enter_offline_callback(self.state_machine.update_command_en)
        self.op_src_mode.add_enter_offline_callback(self.thread_ctrl.stop_thread)

        self.op_src_mode.add_exit_offline_callback(self.state_machine.command_en_ctrl.set_default)
        self.op_src_mode.add_exit_offline_callback(self.state_machine.update_command_en)
        self.op_src_mode.add_exit_offline_callback(self._apply_configuration_parameters)
        self.op_src_mode.add_exit_offline_callback(self._init_idle_state)

        self.op_src_mode.add_enter_operator_callback(
            # adds function to disable commands if no procedure is set
            # lambda allows adding function with argument
            lambda: self.procedure_control.attributes['ProcedureReq'].attach_subscription_callback(
                self.state_machine.disable_commands_if_no_procedure)
        )
        self.op_src_mode.add_enter_operator_callback(
            lambda: self.state_machine.disable_commands_if_no_procedure(
                self.procedure_control.attributes['ProcedureReq'].value
            )
        )

        self.op_src_mode.add_exit_operator_callback(
            # removes function to disables commands if no procedure is set
            self.procedure_control.attributes['ProcedureReq'].remove_subscription_callback
        )

    def enable_pause_loop(self, enable: bool = True):
        """
        Enables or disables the pause loop.

        Args:
            enable (bool): If True, enables the pause loop. If False, disables it.
        """
        self.state_machine.command_en_ctrl.enable_pause_loop(enable)

    def enable_hold_loop(self, enable: bool = True):
        """
        Enables or disables the hold loop.

        Args:
            enable (bool): If True, enables the hold loop. If False, disables it.
        """
        self.state_machine.command_en_ctrl.enable_hold_loop(enable)

    def enable_restart(self, enable: bool = True):
        """
        Enables or disables the restart command.

        Args:
            enable (bool): If True, enables the restart command. If False, disables it.
        """
        self.state_machine.command_en_ctrl.enable_restart(enable)

    def add_configuration_parameter(self, configuration_parameter: SUCParameterElement):
        """
        Adds a configuration parameter to the service.

        Args:
            configuration_parameter (SUCParameterElement): Configuration parameter to add.
        """
        self.configuration_parameters[configuration_parameter.tag_name] = configuration_parameter

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
            self.procedure_control.attributes['ProcedureReq'].init_value = self.procedure_control.default_procedure_id
            self.procedure_control.set_procedure_req(self.procedure_control.default_procedure_id)

    def get_current_procedure(self) -> Procedure:
        """
        Returns the current procedure.

        Returns:
            Procedure: The current procedure.
        """
        return self.procedures[self.procedure_control.get_procedure_cur()]

    def is_state(self, state_str):
        """
        Checks if the current state matches the given state.

        Args:
            state_str (str): State to check.

        Returns:
            bool: True if the current state matches, False otherwise.
        """
        if state_str is self.state_machine.get_current_state_str():
            # handel the case where there are multiple threads for the same state are running
            # (e.g. execute state after restart)
            if self.get_state_stop_event().is_set():
                return False
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
        current_thread = self.thread_ctrl.get_current_thread()
        if not isinstance(current_thread, StoppableThread):
            raise RuntimeError("Current thread is not a state thread. No stop event available.")

        return current_thread.stop_event

    def _init_idle_state(self):
        """
        Initializes the idle state.
        """
        self._state_change_callback()

    def _state_change_callback(self):
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

    def _state_change(self):
        """
        Changes the state. Is automatically called after each state function returns.
        """
        # don't automatically change state for non self-completing procedures
        if self.state_machine.get_current_state_str() == "execute":
            if not self._is_self_completing():
                return
        self.state_machine.state_change()

    def _is_self_completing(self) -> bool:
        """
        Checks if the current Procedure is self-completing.

        Returns:
            bool: True if the current Procedure is self-completing, False otherwise.
        """
        return self.get_current_procedure().attributes['IsSelfCompleting'].value

    def _apply_configuration_parameters(self):
        """
        Applies configuration parameters.
        """
        _logger.debug('Applying service configuration parameters')
        for configuration_parameter in self.configuration_parameters.values():
            configuration_parameter.set_v_out()

    def idle(self):
        """
        Idle state.
        """
        _logger.debug(f"{self.tag_name} - Idle -")
        cycle = 0
        while self.is_state("idle"):
            _logger.debug(f"{self.tag_name} - Idle cycle {cycle}")
            cycle += 1
            time.sleep(3)

    @abstractmethod
    def starting(self):
        """
        Starting state.
        """

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

    def completed(self):
        """
        Completed state.
        """
        if self.state_machine.get_current_state_str() == "completed":
            _logger.debug(f"{self.tag_name} - Completed -")

    def pausing(self):
        """
        Pausing state.
        """
        if self.state_machine.get_current_state_str() == "pausing":
            _logger.debug(f"{self.tag_name} - Pausing -")

    def paused(self):
        """
        Paused state.
        """
        if self.state_machine.get_current_state_str() == "paused":
            _logger.debug(f"{self.tag_name} - Paused -")

    def resuming(self):
        """
        Resuming state.
        """
        if self.state_machine.get_current_state_str() == "resuming":
            _logger.debug(f"{self.tag_name} - Resuming -")

    def holding(self):
        """
        Holding state.
        """
        if self.state_machine.get_current_state_str() == "holding":
            _logger.debug(f"{self.tag_name} - Holding -")

    def held(self):
        """
        Held state.
        """
        if self.state_machine.get_current_state_str() == "held":
            _logger.debug(f"{self.tag_name} - Held -")

    def unholding(self):
        """
        Unholding state.
        """
        if self.state_machine.get_current_state_str() == "unholding":
            _logger.debug(f"{self.tag_name} - Unholding -")

    def stopping(self):
        """
        Stopping state.
        """
        if self.state_machine.get_current_state_str() == "stopping":
            _logger.debug(f"{self.tag_name} - Stopping -")

    def stopped(self):
        """
        Stopped state.
        """
        if self.state_machine.get_current_state_str() == "stopped":
            _logger.debug(f"{self.tag_name} - Stopped -")

    def aborting(self):
        """
        Aborting state.
        """
        if self.state_machine.get_current_state_str() == "aborting":
            _logger.debug(f"{self.tag_name} - Aborting -")

    def aborted(self):
        """
        Aborted state.
        """
        if self.state_machine.get_current_state_str() == "aborted":
            _logger.debug(f"{self.tag_name} - Aborted -")

    def resetting(self):
        """
        Resetting state.
        """
        if self.state_machine.get_current_state_str() == "resetting":
            _logger.debug(f"{self.tag_name} - Resetting -")
