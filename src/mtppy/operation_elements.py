import logging

from mtppy.attribute import Attribute
from mtppy.operation_source_mode import OperationSourceModeOperationElements
from mtppy.suc_data_assembly import SUCOperationElement


_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class AnaMan(SUCOperationElement):
    """
    Analog Operation Element (AnaMan).
    Table 32 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_min: float = 0.0, v_max: float = 100.0,
                 v_scl_min: float = 0.0, v_scl_max: float = 100.0,
                 v_unit: int = 0, init_value: float = 0.0):
        super().__init__(tag_name, tag_description)

        self.v_min = v_min
        self.v_max = v_max
        self.v_scl_min = v_scl_min
        self.v_scl_max = v_scl_max
        self.v_unit = v_unit

        # Attributes with callbacks
        self._add_attribute(Attribute('VOut', float, init_value=init_value))
        self._add_attribute(Attribute('VSclMin', float, init_value=v_scl_min))
        self._add_attribute(Attribute('VSclMax', float, init_value=v_scl_max))
        self._add_attribute(Attribute('VUnit', int, init_value=v_unit))
        self._add_attribute(Attribute('VMan', float, init_value=init_value, sub_cb=self.set_v_man))
        self._add_attribute(Attribute('VMin', float, init_value=v_min))
        self._add_attribute(Attribute('VMax', float, init_value=v_max))
        self._add_attribute(Attribute('VRbk', float, init_value=init_value))
        self._add_attribute(Attribute('VFbk', float, init_value=init_value))

    def valid_value(self, value: float) -> bool:
        return self.v_min <= value <= self.v_max

    def set_v_man(self, value: float):
        _logger.debug(f"VMan set to {value}")
        if self.valid_value(value):
            self.set_v_out(value)
        else:
            _logger.warning(f"VMan {value} out of range ({self.v_min} - {self.v_max})")

    def set_v_out(self, value: float):
        self.attributes['VOut'].set_value(value)
        self.set_v_rbk(value)
        self.set_v_fbk(value)
        _logger.debug(f"VOut set to {value}")

    def set_v_rbk(self, value: float):
        self.attributes['VRbk'].set_value(value)
        _logger.debug(f"VRbk set to {value}")

    def set_v_fbk(self, value: float):
        self.attributes['VFbk'].set_value(value)
        _logger.debug(f"VFbk set to {value}")

    def get_v_out(self) -> float:
        return self.attributes['VOut'].value


class AnaManInt(AnaMan):
    """
    Analog Operation Element with Internal Setpoint and SourceMode (AnaManInt).
    Table 33 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_min: float = 0.0, v_max: float = 100.0,
                 v_scl_min: float = 0.0, v_scl_max: float = 100.0,
                 v_unit: int = 0, init_value: float = 0.0):
        super().__init__(tag_name, tag_description,
                         v_min=v_min, v_max=v_max,
                         v_scl_min=v_scl_min, v_scl_max=v_scl_max,
                         v_unit=v_unit, init_value=init_value)

        self.op_src_mode = OperationSourceModeOperationElements()

        # Extensions (Table 33)
        self._add_attribute(Attribute('WQC', int, init_value=0))
        self._add_attribute(Attribute('VInt', float, init_value=init_value, sub_cb=self.set_v_int))

    def set_v_man(self, value: float):
        _logger.debug(f"VMan set to {value}")
        if self.op_src_mode.attributes['SrcManAct'].value and self.valid_value(value):
            self.set_v_out(value)

    def set_v_int(self, value: float):
        _logger.debug(f"VInt set to {value}")
        if self.op_src_mode.attributes['SrcIntAct'].value and self.valid_value(value):
            self.set_v_out(value)


class DIntMan(SUCOperationElement):
    """
    Discrete Integer Operation Element (DIntMan).
    Table 34 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_min: int = 0, v_max: int = 100,
                 v_scl_min: int = 0, v_scl_max: int = 100,
                 v_unit: int = 0, init_value: int = 0):
        super().__init__(tag_name, tag_description)

        self.v_min = v_min
        self.v_max = v_max
        self.v_scl_min = v_scl_min
        self.v_scl_max = v_scl_max
        self.v_unit = v_unit

        self._add_attribute(Attribute('VOut', int, init_value=init_value))
        self._add_attribute(Attribute('VSclMin', int, init_value=v_scl_min))
        self._add_attribute(Attribute('VSclMax', int, init_value=v_scl_max))
        self._add_attribute(Attribute('VUnit', int, init_value=v_unit))
        self._add_attribute(Attribute('VMan', int, init_value=init_value, sub_cb=self.set_v_man))
        self._add_attribute(Attribute('VMin', int, init_value=v_min))
        self._add_attribute(Attribute('VMax', int, init_value=v_max))
        self._add_attribute(Attribute('VRbk', int, init_value=init_value))
        self._add_attribute(Attribute('VFbk', int, init_value=init_value))

    def valid_value(self, value: int) -> bool:
        return self.v_min <= value <= self.v_max

    def set_v_man(self, value: int):
        _logger.debug(f"VMan set to {value}")
        if self.valid_value(value):
            self.set_v_out(value)
        else:
            _logger.warning(f"VMan {value} out of range ({self.v_min} - {self.v_max})")

    def set_v_out(self, value: int):
        self.attributes['VOut'].set_value(value)
        self.set_v_rbk(value)
        self.set_v_fbk(value)
        _logger.debug(f"VOut set to {value}")

    def set_v_rbk(self, value: int):
        self.attributes['VRbk'].set_value(value)
        _logger.debug(f"VRbk set to {value}")

    def set_v_fbk(self, value: int):
        self.attributes['VFbk'].set_value(value)
        _logger.debug(f"VFbk set to {value}")

    def get_v_out(self) -> int:
        return self.attributes['VOut'].value


class DIntManInt(DIntMan):
    """
    Integer Operation Element with Internal Setpoint and SourceMode (DIntManInt).
    Table 35 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_min: int = 0, v_max: int = 100,
                 v_scl_min: int = 0, v_scl_max: int = 100,
                 v_unit: int = 0, init_value: int = 0):
        super().__init__(tag_name, tag_description,
                         v_min=v_min, v_max=v_max,
                         v_scl_min=v_scl_min, v_scl_max=v_scl_max,
                         v_unit=v_unit, init_value=init_value)

        self.op_src_mode = OperationSourceModeOperationElements()

        # Extensions (Table 35)
        self._add_attribute(Attribute('WQC', int, init_value=0))
        self._add_attribute(Attribute('VInt', int, init_value=init_value, sub_cb=self.set_v_int))

    def set_v_man(self, value: int):
        _logger.debug(f"VMan set to {value}")
        if self.op_src_mode.attributes['SrcManAct'].value and self.valid_value(value):
            self.set_v_out(value)

    def set_v_int(self, value: int):
        _logger.debug(f"VInt set to {value}")
        if self.op_src_mode.attributes['SrcIntAct'].value and self.valid_value(value):
            self.set_v_out(value)


class BinMan(SUCOperationElement):
    """
    Binary Operation Element (BinMan).
    Table 36 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_state0: str = 'Off', v_state1: str = 'On',
                 init_value: bool = False):
        super().__init__(tag_name, tag_description)

        self.v_state0 = v_state0
        self.v_state1 = v_state1

        self._add_attribute(Attribute('VOut', bool, init_value=init_value))
        self._add_attribute(Attribute('VState0', str, init_value=v_state0))
        self._add_attribute(Attribute('VState1', str, init_value=v_state1))
        self._add_attribute(Attribute('VMan', bool, init_value=init_value, sub_cb=self.set_v_man))
        self._add_attribute(Attribute('VRbk', bool, init_value=init_value))
        self._add_attribute(Attribute('VFbk', bool, init_value=init_value))

    def set_v_man(self, value: bool):
        _logger.debug(f"VMan set to {value}")
        self.set_v_out(value)

    def set_v_out(self, value: bool):
        self.attributes['VOut'].set_value(value)
        self.set_v_rbk(value)
        self.set_v_fbk(value)
        _logger.debug(f"VOut set to {value}")

    def set_v_rbk(self, value: bool):
        self.attributes['VRbk'].set_value(value)
        _logger.debug(f"VRbk set to {value}")

    def set_v_fbk(self, value: bool):
        self.attributes['VFbk'].set_value(value)
        _logger.debug(f"VFbk set to {value}")

    def get_v_out(self) -> bool:
        return self.attributes['VOut'].value


class BinManInt(BinMan):
    """
    Binary Operation Element with Internal Setpoint and SourceMode (BinManInt).
    Table 37 from VDI/VDE/NAMUR 2658-3.
    """

    def __init__(self, tag_name: str, tag_description: str = '',
                 v_state0: str = 'Off', v_state1: str = 'On',
                 init_value: bool = False):
        super().__init__(tag_name, tag_description,
                         v_state0=v_state0, v_state1=v_state1,
                         init_value=init_value)

        self.op_src_mode = OperationSourceModeOperationElements()

        # Extensions (Table 37)
        self._add_attribute(Attribute('WQC', int, init_value=0))
        self._add_attribute(Attribute('VInt', bool, init_value=init_value, sub_cb=self.set_v_int))

    def set_v_man(self, value: bool):
        _logger.debug(f"VMan set to {value}")
        if self.op_src_mode.attributes['SrcManAct'].value:
            self.set_v_out(value)

    def set_v_int(self, value: bool):
        _logger.debug(f"VInt set to {value}")
        if self.op_src_mode.attributes['SrcIntAct'].value:
            self.set_v_out(value)
