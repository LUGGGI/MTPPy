import logging

from collections.abc import Callable
from typing import Any


_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class Attribute:
    def __init__(self, name: str, data_type, init_value, sub_cb: Callable[[Any], None] = None):
        """
        Attribute represents an elementary object (attribute or parameter) of a data assembly. Depending on whether
        subscription callback is defined or not, it might be an monitored object or a static OPC UA node.

        Args:
            name (str): Attribute name.
            data_type (type): Attribute type.
            init_value (type): Initial value of the attribute.
            sub_cb (Callable[[Any], None], optional): Subscription callback. 
                If defined, the attribute will be monitored.
        """
        self.name = name
        self.type = data_type
        corrected_value = self._correct_type(init_value)
        self.init_value = corrected_value
        self.value = corrected_value
        self.comm_obj = None
        self.sub_cb: Callable[[Any], None] = sub_cb

    def set_value(self, value):
        """
        Set value of the attribute.

        Args:
            value (type): Value.

        Returns:
            bool: Returns True if value was applied.
        """
        self.value = self._correct_type(value)

        if self.sub_cb is not None:
            self.sub_cb(self.value)

        if self.comm_obj is not None:
            if self.comm_obj.write_value_callback is not None:
                self.comm_obj.write_value_callback(self.value)

        _logger.debug(f'New value for {self.name} is {self.value}')
        return True

    def _correct_type(self, value):
        """
        Converts a value to the attribute type.

        Args:
            value (type): Value.

        Returns:
            type: Converted value. If conversion is not possible, returns a default value of that type.

        Raises:
            Exception: If conversion fails.
        """
        try:
            converted_value = self.type(value)
            return converted_value
        except Exception:
            return self.type()

    def attach_communication_object(self, communication_object):
        """
        Attach a communication object to the attribute, e.g. if an OPC UA node needs to be created for the attribute.

        Args:
            communication_object (type): Communication object.
        """
        self.comm_obj = communication_object

    def attach_subscription_callback(self, sub_cb: Callable[[Any], None]):
        """
        Attach a subscription callback to the attribute.

        Args:
            sub_cb (Callable[[Any], None]): 
                Subscription callback function that will be called when the value changes.
        """
        self.sub_cb = sub_cb

    def remove_subscription_callback(self):
        """
        Remove the subscription callback from the attribute.
        """
        self.sub_cb = None
