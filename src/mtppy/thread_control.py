import logging
from threading import Thread, Event
from collections.abc import Callable

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class ThreadControl:
    def __init__(self, service_name: str = ''):
        """
        Represents a thread control to be able to run with multithreading.
        """
        self.service_name = service_name
        self.thread: Thread = None
        self.running_state = ''
        self.requested_state = ''
        self.callback_function: Callable = None
        self.exception_event = Event()
        self.exception: Exception = None

    def request_state(self, state: str, cb_function: Callable):
        _logger.debug(f'State {state} requested')
        self.requested_state = state
        self.callback_function = cb_function

    def reallocate_running_thread(self):
        _logger.debug(f'Reallocate thread to state {self.requested_state}')
        if self.requested_state is not self.running_state:
            self.thread = Thread(target=self.run_thread, args=(self.callback_function,),
                                 name=f"{self.service_name}_{self.requested_state}")
            self.thread.start()
            self.running_state = self.requested_state

    def run_thread(self, target_function: Callable):
        """
        Runs the given target function in a new thread.
        :param target_function: The function to run in the thread.
        """
        try:
            target_function()
        except Exception as e:
            self.exception = e
            self.exception_event.set()
