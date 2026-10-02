import sys
import logging
from collections import deque

LOG_FORMAT = "[%(asctime)s][%(levelname)s][%(name)s] %(message)s"
DATE_FORMAT = "%H:%M:%S"
RECENT_LOG_SIZE = 100

# LOG_LEVEL config value -> logging level, anything larger means ERROR
LEVELS = {0: logging.DEBUG, 1: logging.DEBUG, 2: logging.INFO, 3: logging.WARNING}

# third-party loggers that are too verbose at DEBUG
QUIET_LOGGERS = ["urllib3", "charset_normalizer", "chardet"]


class RecentLogHandler(logging.Handler):
    """ Keeps the latest formatted log lines in memory """
    def __init__(self, capacity):
        super().__init__()
        self.lines = deque(maxlen=capacity)

    def emit(self, record):
        # logging.Handler.handle() holds self.lock while calling emit
        self.lines.append(self.format(record))

    def get_lines(self):
        with self.lock:
            return list(self.lines)


_recent_handler = RecentLogHandler(RECENT_LOG_SIZE)


def setup(level=0):
    """ Configure the root logger. Can be called again to change the level.
    level: LOG_LEVEL number (0~4) or a logging level name such as "INFO" """
    root = logging.getLogger()
    if _recent_handler not in root.handlers:
        formatter = logging.Formatter(LOG_FORMAT, DATE_FORMAT)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        _recent_handler.setFormatter(formatter)
        root.addHandler(console_handler)
        root.addHandler(_recent_handler)
        for name in QUIET_LOGGERS:
            logging.getLogger(name).setLevel(logging.WARNING)
    if isinstance(level, str):
        root.setLevel(level.upper())
    else:
        root.setLevel(LEVELS.get(level, logging.ERROR))


def get_log_record():
    """ The latest log lines joined by newlines """
    return "\n".join(_recent_handler.get_lines())
