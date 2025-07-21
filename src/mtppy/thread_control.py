import logging
from threading import Thread
from datetime import datetime
import asyncio

from apscheduler.schedulers.asyncio import AsyncIOScheduler

_logger = logging.getLogger(f"mtp.{__name__.split('.')[-1]}")


class ThreadControl:
    def __init__(self, scheduler: callable = None):
        """
        Represents a thread control to be able to run with multithreading.
        :param scheduler: Scheduler to run the jobs.
        """
        self.scheduler: AsyncIOScheduler = scheduler
        self.job_event = asyncio.Event()
        self.exception: Exception = None
        self.exception_event = asyncio.Event()
        self.thread = None
        self.running_state = ''
        self.requested_state = ''
        self.callback_function = None

    def request_state(self, state: str, cb_function: callable):
        _logger.debug(f'State {state} requested')
        self.requested_state = state
        self.callback_function = cb_function

    def reallocate_running_thread(self):
        _logger.debug(f'Reallocate thread to state {self.requested_state}')
        if self.requested_state is not self.running_state:
            self.job_event.set()

            self.scheduler.add_job(
                self.run_job, 'date', run_date=datetime.now(), name=self.requested_state,
                misfire_grace_time=None)
            self.running_state = self.requested_state

    async def run_job(self):
        self.job_event.clear()
        tasks: list[asyncio.Task] = [
            asyncio.create_task(self.job_event.wait(), name='cancel_event'),
            asyncio.create_task(self.callback_function(), name=self.requested_state)
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        for task in pending:
            task.cancel()

        try:
            if tasks[1].exception() != None:
                raise tasks[1].exception()
        except asyncio.exceptions.InvalidStateError as e:
            pass
        except Exception as e:
            self.exception = e
            self.exception_event.set()
            _logger.warning(f"Task {tasks[1].get_name()} raised an exception: {e}")
