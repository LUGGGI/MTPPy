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
        self.sub_cb: Callable[[Any], None] = None
        self.sub_cbs: dict[str, Callable[[Any], None]] = {}
        if sub_cb is not None:
            self.sub_cbs[self.name] = sub_cb
            self.sub_cb = self._call_callbacks

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

    def _call_callbacks(self, value):
        """
        Call all subscription callbacks with the new value.

        Args:
            value (type): New value to pass to the callbacks.
        """
        for cb in self.sub_cbs.values():
            cb(value)

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

    def attach_subscription_callback(self, sub_cb: Callable[[Any], None], cb_name: str = None):
        """
        Attach a subscription callback to the attribute.

        Args:
            sub_cb (Callable[[Any], None]): 
                Subscription callback function that will be called when the value changes.
            cb_name (str, optional): Name of the callback. 
                If not provided, the attribute name will be used.
        """
        if cb_name is None:
            cb_name = self.name
        self.sub_cbs[cb_name] = sub_cb
        _logger.debug(f'Subscription callback {cb_name} added to attribute {self.name}')

        # add the callback to the sub_cb
        self.sub_cb = self._call_callbacks

    def remove_subscription_callback(self, cb_name: str = None):
        """
        Remove the subscription callback from the attribute.

        Args:
            cb_name (str, optional): Name of the callback to remove. 
            If not provided, the callback with the attribute name will be removed.
        """
        if cb_name is None:
            cb_name = self.name

        if cb_name in self.sub_cbs:
            self.sub_cbs.pop(cb_name)
            _logger.debug(f'Subscription callback {cb_name} removed from attribute {self.name}')

        # remove the sub_cb if no callbacks left
        if self.sub_cbs == {}:
            self.sub_cb = None
