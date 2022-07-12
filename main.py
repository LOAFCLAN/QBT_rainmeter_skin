import logging
import os
import pathlib
import traceback
from threading import Thread

try:
    logging.basicConfig(
        level=logging.INFO,
        format=r"[%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(funcName)s - %(message)s]",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=r"D:\Rainmeter\Logs\log.log")
except Exception as e:
    logging.basicConfig(
        level=logging.INFO,
        format=r"[%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(funcName)s - %(message)s]")
    logging.error(f"Error in InhibitorPlugin: {e}")

import asyncio

# import auto_update
import rm_interface


class Rain:
    """This whole class is just a pass-through to the rainmeter interface"""

    def __init__(self):
        """Never actually called, reload is the actual entry point"""
        logging.info("Initializing Rainmeter Script")
        self.rainmeter = None
        self.rainmeter_interface = None
        self.updater = None
        self.event_loop = None
        self.task = None
        self.background_thread = None

    async def on_new_version(self):
        pass

    async def on_update_restart(self):
        pass

    def _task_done(self, task):
        """Called when the rainmeter plugin is done with the task"""
        pass

    def Reload(self, rm, maxValue) -> None:
        try:
            rm.RmLog(rm.LOG_NOTICE, "Reload Called")
            self.rainmeter = rm
            logging.info("Reload called")
            self.event_loop = asyncio.new_event_loop()
            self.task = self.event_loop.create_task(self.true_init())

            self.background_thread = Thread(target=self._start_asyncio, name="Dear god I am sorry")
            self.background_thread.start()

            # Log info about the task
            logging.info(f"Task: {self.task}")
            logging.info(f"Task.done: {self.task.get_stack()}")

            logging.info(f"Thread: {self.background_thread}")
            logging.info(f"Thread alive: {self.background_thread.is_alive()}")

        except Exception as e:
            logging.error(f"Error in Reload: {e}")

    def _start_asyncio(self):
        """Start the asyncio event loop"""
        try:
            logging.info("Starting asyncio event loop")
            self.event_loop.run_forever()
            logging.warning("Well shit")
        except Exception as e:
            logging.error(f"Error in _start_asyncio: {e}")

    async def true_init(self):
        """This is the actual initialization of the plugin"""
        logging.info("Initializing rainmeter interface")
        try:
            self.rainmeter.RmLog(self.rainmeter.LOG_NOTICE, "Creating Rainmeter Interface")
            logging.info("Creating rainmeter interface")
            self.rainmeter_interface = rm_interface.RainMeterInterface(self.rainmeter, self.event_loop)
            logging.info("Initialized rainmeter interface")
            self.rainmeter.RmLog(self.rainmeter.LOG_NOTICE, "Created Rainmeter Interface, creating updater")
        except Exception as e:
            logging.error(f"Error in true_init: {e}\n{traceback.format_exc()}")

    def Update(self) -> None:
        """Called by the rainmeter plugin"""
        try:
            if self.rainmeter_interface is None:
                logging.critical("rainmeter_interface failed to initialize")
            else:
                task = self.event_loop.create_task(self.rainmeter_interface.update())
                task.add_done_callback(self._task_done)
        except Exception as e:
            logging.error(f"Error in Update: {e}")

    def GetString(self) -> str:
        return ""

    def ExecuteBang(self, args) -> None:
        """Called by the rainmeter plugin"""
        try:
            task = self.event_loop.create_task(self.rainmeter_interface.execute_bang(args))
        except Exception as e:
            logging.error(f"Error in ExecuteBang: {e}")

    def Finalize(self) -> None:
        """Called by the rainmeter plugin"""
        try:
            task = self.event_loop.create_task(self.rainmeter_interface.tear_down())
            # Wait for the task to finish
            task.add_done_callback(lambda _: task.result())
        except Exception as e:
            logging.error(f"Error in Finalize: {e}")
