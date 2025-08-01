import logging

from mtppy.attribute import Attribute
from mtppy.state_codes import StateCodes
from mtppy.command_codes import CommandCodes
from mtppy.command_en_control import CommandEnControl
from mtppy.operation_source_mode import OperationSourceMode
from mtppy.procedure_control import ProcedureControl
StateCodes = StateCodes()
CommandCodes = CommandCodes()

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class StateMachine:
    def __init__(self, operation_source_mode: OperationSourceMode,
                 procedure_control: ProcedureControl,
                 execution_routine: callable):
        """
        Represents a state machine for a service.

        Args:
            operation_source_mode (OperationSourceMode): Operation and source mode control.
            procedure_control (ProcedureControl): Procedure control.
            execution_routine (callable): Execution routine for state changing.
        """

        self.attributes = {
            'CommandOp': Attribute('CommandOp', int, init_value=0, sub_cb=self.set_command_op),
            'CommandInt': Attribute('CommandInt', int, init_value=0, sub_cb=self.set_command_int),
            'CommandExt': Attribute('CommandExt', int, init_value=0, sub_cb=self.set_command_ext),

            'StateCur': Attribute('StateCur', int, init_value=16),
            'CommandEn': Attribute('CommandEn', int, init_value=0),
        }

        self.op_src_mode: OperationSourceMode = operation_source_mode
        self.procedure_control: ProcedureControl = procedure_control
        self.execution_routine = execution_routine
        self.command_en_ctrl = CommandEnControl()

        self.act_state = StateCodes.idle
        self.prev_state = StateCodes.idle

        self.op_src_mode.add_enter_operator_callback(
            # adds function to disable commands if no procedure is set
            # lambda allows adding function with argument
            lambda: self.procedure_control.attributes['ProcedureReq'].attach_subscription_callback(
                self.disable_commands_if_no_procedure)
        )
        self.op_src_mode.add_exit_operator_callback(
            # removes function to disables commands if no procedure is set
            self.procedure_control.attributes['ProcedureReq'].remove_subscription_callback()
        )

    def set_command_op(self, value: int):
        if self.op_src_mode.attributes['StateOpAct'].value:
            self.command_execution(value)

    def set_command_int(self, value: int):
        if self.op_src_mode.attributes['StateAutAct'].value and self.op_src_mode.attributes['SrcIntAct'].value:
            self.command_execution(value)

    def set_command_ext(self, value: int):
        if self.op_src_mode.attributes['StateAutAct'].value and self.op_src_mode.attributes['SrcExtAct'].value:
            self.command_execution(value)

    def command_execution(self, com_var: int):
        if com_var not in CommandCodes.get_list_int():
            _logger.debug(f'Command Code {com_var} does not exist')
            return

        cmd_str = CommandCodes.int_code[com_var]
        if not self.command_en_ctrl.is_enabled(cmd_str):
            _logger.debug(
                f'CommandEn does not permit to execute {cmd_str} from state {self.get_current_state_str()}')
            return
        else:
            _logger.debug(f'CommandEn permits to execute {cmd_str}')

        # execute the command, if it is enabled will change the state thread to the requested state
        eval(f'self.{CommandCodes.int_code[com_var]}()')

        # reset the command operation code
        if self.op_src_mode.attributes['StateOpAct'].value:
            self.attributes['CommandOp'].set_value(0)
        elif self.op_src_mode.attributes['StateAutAct'].value and self.op_src_mode.attributes['SrcIntAct'].value:
            self.attributes['CommandInt'].set_value(0)
        elif self.op_src_mode.attributes['StateAutAct'].value and self.op_src_mode.attributes['SrcExtAct'].value:
            self.attributes['CommandExt'].set_value(0)

    def start(self):
        if self.command_en_ctrl.is_enabled('start'):
            # removes the function to disables commands if no procedure is set
            self.procedure_control.attributes['ProcedureReq'].remove_subscription_callback()

            self.procedure_control.set_procedure_cur()
            self.procedure_control.attributes['ProcedureOp'].set_value(0)
            self.procedure_control.attributes['ProcedureInt'].set_value(0)
            self.procedure_control.attributes['ProcedureExt'].set_value(0)
            self.procedure_control.apply_procedure_parameters()
            self._change_state_to(StateCodes.starting)

    def restart(self):
        if self.command_en_ctrl.is_enabled('restart'):
            self._change_state_to(StateCodes.starting)

    def complete(self):
        if self.command_en_ctrl.is_enabled('complete'):
            self._change_state_to(StateCodes.completing)

    def pause(self):
        if self.command_en_ctrl.is_enabled('pause'):
            self._change_state_to(StateCodes.pausing)

    def resume(self):
        if self.command_en_ctrl.is_enabled('resume'):
            self._change_state_to(StateCodes.resuming)

    def reset(self):
        if self.command_en_ctrl.is_enabled('reset'):
            self._change_state_to(StateCodes.resetting)
            # adds function to disable commands if no procedure is set
            self.procedure_control.attributes['ProcedureReq'].attach_subscription_callback(
                self.disable_commands_if_no_procedure)

    def hold(self):
        if self.command_en_ctrl.is_enabled('hold'):
            self._change_state_to(StateCodes.holding)

    def unhold(self):
        if self.command_en_ctrl.is_enabled('unhold'):
            self._change_state_to(StateCodes.unholding)

    def stop(self):
        if self.command_en_ctrl.is_enabled('stop'):
            self._change_state_to(StateCodes.stopping)

    def abort(self):
        if self.command_en_ctrl.is_enabled('abort'):
            self._change_state_to(StateCodes.aborting)

    def state_change(self):
        if self.act_state == StateCodes.starting:
            self._change_state_to(StateCodes.execute)
        elif self.act_state == StateCodes.starting:
            self._change_state_to(StateCodes.execute)
        elif self.act_state == StateCodes.execute:
            self._change_state_to(StateCodes.completing)
        elif self.act_state == StateCodes.completing:
            self._change_state_to(StateCodes.completed)
        elif self.act_state == StateCodes.pausing:
            self._change_state_to(StateCodes.paused)
        elif self.act_state == StateCodes.resuming:
            self._change_state_to(StateCodes.execute)
        elif self.act_state == StateCodes.resetting:
            self._change_state_to(StateCodes.idle)
        elif self.act_state == StateCodes.holding:
            self._change_state_to(StateCodes.held)
        elif self.act_state == StateCodes.unholding:
            self._change_state_to(StateCodes.execute)
        elif self.act_state == StateCodes.stopping:
            self._change_state_to(StateCodes.stopped)
        elif self.act_state == StateCodes.aborting:
            self._change_state_to(StateCodes.aborted)

    def _change_state_to(self, new_state: int):
        self.act_state = new_state
        self.attributes['StateCur'].set_value(new_state)
        new_state_str = StateCodes.int_code[new_state]
        self.command_en_ctrl.execute(new_state_str)
        self.update_command_en()
        self.execution_routine()
        _logger.debug(f'Service state changed to {new_state}')

    def update_command_en(self):
        """
        Updates the CommandEn attribute based on the current enabled flags.
        """
        self.attributes['CommandEn'].set_value(self.command_en_ctrl.get_command_en())

    def get_current_state_str(self) -> str:
        """
        Get the current state as a string.

        Returns:
            str: Current state as a string.
        """
        return StateCodes.int_code[self.act_state]

    def disable_commands_if_no_procedure(self, value: int):
        """
        Disables all commands if value is 0 and the current state is idle.

        Args:
            value (int): Value of the ProcedureReq attribute.
        """
        if self.act_state is StateCodes.idle and value == 0:
            self.command_en_ctrl.disable_all()
        else:
            self.command_en_ctrl.execute(self.get_current_state_str())
        self.update_command_en()
