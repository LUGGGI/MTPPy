import logging
from threading import Thread, Event
from collections.abc import Callable

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class ThreadControl:
    def __init__(self, service_name: str = ''):
        """
        Represents a thread control to be able to run with multithreading.

        Args:
            service_name (str): Name of the service.
        """
        self.service_name = service_name
        self.thread: Thread = None
        self.running_state = ''
        self.requested_state = ''
        self.callback_function: Callable = None
        self.exception_event = Event()
        self.exception: Exception = None

    def request_state(self, state: str, cb_function: Callable):
        """
        Requests a state change and sets the callback function.

        Args:
            state (str): The requested state.
            cb_function (Callable): The callback function to execute.
        """
        _logger.debug(f'State {state} requested')
        self.requested_state = state
        self.callback_function = cb_function

    def reallocate_running_thread(self):
        """
        Reallocates the running thread to the requested state.
        """
        _logger.debug(f'Reallocate thread to state {self.requested_state}')
        if self.requested_state is not self.running_state:
            self.thread = Thread(target=self.run_thread, args=(self.callback_function,),
                                 name=f"{self.service_name}_{self.requested_state}")
            self.thread.start()
            self.running_state = self.requested_state

    def run_thread(self, target_function: Callable):
        """
        Runs the given target function. Sets the exception if it occurs.

        Args:
            target_function (Callable): The function to run in the thread.
        """
        try:
            target_function()
        except Exception as e:
            self.exception = e
            self.exception_event.set()
