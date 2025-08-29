from mtppy.attribute import Attribute
from abc import abstractmethod


class SUCDataAssembly:
    def __init__(self, tag_name: str, tag_description: str = ''):
        self.tag_name = tag_name
        self.tag_description = tag_description
        self.attributes = {
            'tag_name': Attribute('tag_name', str, init_value=self.tag_name),
            'tag_description': Attribute('tag_description', str, init_value=self.tag_description)
        }

    def _add_attribute(self, attribute: Attribute):
        self.attributes[attribute.name] = attribute


class SUCIndicatorElement(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('OSLevel', int, init_value=0))
        self._add_attribute(Attribute('WQC', int, init_value=255))

    @abstractmethod
    def set_v(self, value):
        """
        Set the value of the 'V' attribute.
        """
        pass


class SUCOperationElement(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('OSLevel', int, init_value=0))


class SUCParameterElement(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('OSLevel', int, init_value=0))
        self._add_attribute(Attribute('WQC', int, init_value=255))

    @abstractmethod
    def set_v_int(self, value):
        """
        Set Parameter value if StateIntAct.
        """
        pass

    @abstractmethod
    def get_v_out(self):
        """
        Get the current value of VOut (current parameter value).
        """
        pass

    @abstractmethod
    def set_v_fbk(self, value):
        """
        Set VFbk (feedback value) to the specified value.
        """
        pass


class SUCActiveElement(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('OSLevel', int, init_value=0))
        self._add_attribute(Attribute('WQC', int, init_value=255))


class SUCServiceControl(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('OSLevel', int, init_value=0))
        self._add_attribute(Attribute('WQC', int, init_value=255))
        self._add_attribute(Attribute('PosTextID', int, init_value=0))
        self._add_attribute(Attribute('InteractQuestionID', int, init_value=0))
        self._add_attribute(Attribute('InteractAnswerID', int, init_value=0))


class SUCDiagnosticElement(SUCDataAssembly):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('WQC', int, init_value=255))


class SUCHealthStateView(SUCDiagnosticElement):
    def __init__(self, tag_name: str, tag_description: str):
        super().__init__(tag_name, tag_description)


class SUCServiceProcedure(SUCHealthStateView):
    def __init__(self, procedure_id: int, tag_name: str, tag_description: str, is_self_completing=False,
                 is_default=True):
        super().__init__(tag_name, tag_description)
        self._add_attribute(Attribute('IsSelfCompleting', bool, init_value=is_self_completing))
        self._add_attribute(Attribute('ProcedureId', int, init_value=procedure_id))
        self._add_attribute(Attribute('IsDefault', bool, init_value=is_default))
