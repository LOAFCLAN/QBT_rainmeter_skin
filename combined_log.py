import logging


class CombinedLogHandler(logging.Handler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_handlers = []

    def emit(self, record):
        for handler in self.log_handlers:
            handler.emit(record)

class CombinedLogger(logging.Logger):

    def __init__(self, name, level=logging.NOTSET):
        super().__init__(name, level)
        self.addHandler(CombinedLogHandler())