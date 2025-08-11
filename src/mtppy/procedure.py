import logging

from mtppy.suc_data_assembly import *

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class Procedure(SUCServiceProcedure):
    def __init__(self, procedure_id: int, tag_name: str, tag_description: str = '', is_self_completing: bool = False,
                 is_default: bool = False):
        """
        Represents a procedure of a service.

        Args:
            procedure_id (int): Procedure id. Can't be equal or less than 0.
            tag_name (str): Tag name of the procedure.
            tag_description (str): Tag description of the procedure.
            is_self_completing (bool): Self-completing or not.
            is_default (bool): Default or not.
        """
        if procedure_id <= 0:
            raise ValueError(f"{tag_name}: Procedure ID can't be equal or less than 0.")
        super().__init__(procedure_id, tag_name, tag_description, is_self_completing, is_default)
        self.procedure_parameters: dict[str, SUCOperationElement] = {}
        self.process_value_ins = {}
        self.report_values: dict[str, SUCIndicatorElement] = {}
        self.process_value_outs: dict[str, SUCIndicatorElement] = {}

    def add_procedure_parameter(self, procedure_parameter: SUCOperationElement):
        """
        Adds a procedure parameter to the procedure.

        Args:
            procedure_parameter (SUCOperationElement): Procedure parameter.

        Raises:
            TypeError: If procedure_parameter is not an instance of SUCOperationElement.
        """
        if isinstance(procedure_parameter, SUCOperationElement):
            self.procedure_parameters[procedure_parameter.tag_name] = procedure_parameter
        else:
            raise TypeError()

    def add_procedure_value_in(self, process_value_in):
        """
        Adds a value in to the procedure. NOT IMPLEMENTED.

        Args:
            process_value_in: Value in.

        Raises:
            NotImplementedError: Always raised as the method is not implemented.
        """
        raise NotImplementedError()

    def add_report_value(self, report_value: SUCIndicatorElement):
        """
        Adds a report value to the procedure.

        Args:
            report_value (SUCIndicatorElement): Report value.

        Raises:
            TypeError: If report_value is not an instance of SUCIndicatorElement.
        """
        if isinstance(report_value, SUCIndicatorElement):
            self.report_values[report_value.tag_name] = report_value
        else:
            raise TypeError()

    def add_procedure_value_out(self, process_value_out: SUCIndicatorElement):
        """
        Adds a value out to the procedure.

        Args:
            process_value_out (SUCIndicatorElement): Value out.

        Raises:
            TypeError: If process_value_out is not an instance of SUCIndicatorElement.
        """
        if isinstance(process_value_out, SUCIndicatorElement):
            self.process_value_outs[process_value_out.tag_name] = process_value_out
        else:
            raise TypeError()

    def apply_procedure_parameters(self):
        """
        Applies procedure parameters.
        """
        _logger.debug('Applying procedure parameters')
        for procedure_parameter in self.procedure_parameters.values():
            procedure_parameter.set_v_out()
