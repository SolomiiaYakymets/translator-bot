import os
import sys
from loguru import logger


def initialize_logger(login):
    logs_directory = "logs"
    os.makedirs(logs_directory, exist_ok=True)

    logger.add(
        f"{logs_directory}/{login}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
        level="DEBUG",
        rotation="10 MB"
    )


file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
logger.add(
    "logs/main_log.log",
    rotation="10 MB",
    retention="10 days",
    format=file_format,
    level="TRACE"
)


logger.add(
    "logs/errors.log",
    rotation="10 MB",
    retention="10 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    level="ERROR"
)


logger.add(
    sys.stdout,
    colorize=True,
    format="{time:YYYY-MM-DD HH:mm:ss} | <level>{message}</level>",
    level="TRACE"
)
