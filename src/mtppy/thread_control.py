import logging
from threading import Thread, Event, current_thread
from collections.abc import Callable

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class StoppableThread(Thread):
    """
    A thread that can be told stop by setting an event.
    """

    def __init__(self, target=None, name=None, args=(), kwargs=None):
        super().__init__(target=target, name=name, args=args, kwargs=kwargs)
        self.stop_event = Event()

    def stop(self):
        self.stop_event.set()


class ThreadControl:
    def __init__(self, service_name: str = '', state_change_function: Callable = None):
        """
        Represents a thread control to be able to run with multithreading.

        Args:
            service_name (str): Name of the service.
            state_change_function (Callable): Function to call after a state completes.
        """
        self.service_name = service_name
        self.state_change_function = state_change_function
        self.thread: StoppableThread = None
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
            # stop the current thread if it is running
            if self.thread and self.thread.is_alive() and self.thread is not current_thread():
                _logger.debug(f'Stopping thread {self.thread.name}')
                self.thread.stop()

            self.thread = StoppableThread(target=self.run_thread, args=(self.callback_function,),
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
            try:
                target_function()
                # changes state for transitional states
                # if self.state_change_function:
                #     self.state_change_function()
            # Catch InterruptedError thrown by stop events. Should not cause an error.
            except InterruptedError:
                _logger.debug("Stop event was set, stopping thread execution.")

        except Exception as e:
            self.exception = e
            self.exception_event.set()
