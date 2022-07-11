import asyncio
import rm_interface
import logging

logging.basicConfig(level=logging.INFO,
                    format=r"[%(asctime)s - %(levelname)s - %(threadName)s - %(name)s - %(funcName)s - %(message)s]")


class Rain:
    """This whole class is just a pass-through to the rainmeter interface"""

    def __init__(self):
        """Never actually called, reload is the actual entry point"""
        self.rainmeter = None
        self.rainmeter_interface = None

    def Reload(self, rm, maxValue) -> None:
        self.rainmeter = rm
        self.rainmeter_interface = rm_interface.RainMeterInterface(rm)

    def Update(self) -> None:
        """Called by the rainmeter plugin"""
        asyncio.create_task(self.rainmeter_interface.update())

    def GetString(self) -> str:
        pass

    def ExecuteBang(self, args) -> None:
        """Called by the rainmeter plugin"""
        asyncio.create_task(self.rainmeter_interface.execute_bang(args))

    def Finalize(self) -> None:
        """Called by the rainmeter plugin"""
        task = asyncio.create_task(self.rainmeter_interface.tear_down())
        # Wait for the task to finish
        task.add_done_callback(lambda _: task.result())
