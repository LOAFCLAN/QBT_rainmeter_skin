import logging
import os

try:
    logging.basicConfig(
        level=logging.INFO,
        format=r"[%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(funcName)s - %(message)s]",
        datefmt="%Y-%m-%d %H:%M:%S",
        filename=r"log.txt")
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
        logging.info("Initializing")
        self.rainmeter = None
        self.rainmeter_interface = None
        self.updater = None

    async def on_new_version(self):
        pass

    async def on_update_restart(self):
        pass

    def _task_done(self, task):
        """Called when the rainmeter plugin is done with the task"""
        try:
            task.result()
        except Exception as e:
            logging.error(f"Error in _task_done: {e}")

    def Reload(self, rm, maxValue) -> None:
        try:
            rm.RmLog(rm.LOG_NOTICE, "Reload Called")
            logging.info("Reload called")
            self.rainmeter = rm
            self.rainmeter_interface = rm_interface.RainMeterInterface(rm)
            # self.updater = auto_update.GithubUpdater("JayFromProgramming", "QBT_rainmeter_skin",
            #                                          self.on_update_restart, self.on_new_version)
            # asyncio.create_task(self.updater.run())
        except Exception as e:
            logging.error(f"Error in Reload: {e}")

    def Update(self) -> None:
        """Called by the rainmeter plugin"""
        try:
            task = asyncio.create_task(self.rainmeter_interface.update())
            task.add_done_callback(self._task_done)
        except Exception as e:
            logging.error(f"Error in Update: {e}")

    def GetString(self) -> str:
        return ""

    def ExecuteBang(self, args) -> None:
        """Called by the rainmeter plugin"""
        try:
            task = asyncio.create_task(self.rainmeter_interface.execute_bang(args))
        except Exception as e:
            logging.error(f"Error in ExecuteBang: {e}")

    def Finalize(self) -> None:
        """Called by the rainmeter plugin"""
        try:
            task = asyncio.create_task(self.rainmeter_interface.tear_down())
            # Wait for the task to finish
            task.add_done_callback(lambda _: task.result())
        except Exception as e:
            logging.error(f"Error in Finalize: {e}")


