"""
Centralized logging configuration using loguru
"""

import sys
from pathlib import Path

from loguru import logger

_logging_configured = False


def configure_logging(
    level: str = "INFO",
    log_file: str | None = None,
) -> None:
    """
    Configure loguru logger with specified level and optional file output.

    This function sets up logging for the entire champi_stt package and all dependencies.
    It removes any existing handlers and configures new ones with the specified log level.

    Can be called multiple times safely - only configures once.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for persistent logging
    """
    global _logging_configured

    # Only configure once to avoid removing library loggers
    if _logging_configured:
        return

    # Remove all existing handlers
    logger.remove()

    # Configure format
    log_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )

    # Add console handler
    logger.add(
        sys.stderr,
        format=log_format,
        level=level.upper(),
        colorize=True,
        backtrace=True,
        diagnose=True,
    )

    # Add file handler if specified
    if log_file:
        log_path = Path(log_file).expanduser()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        logger.add(
            str(log_path),
            format=log_format,
            level=level.upper(),
            rotation="10 MB",
            retention="1 week",
            compression="zip",
            backtrace=True,
            diagnose=True,
        )

    # Intercept standard logging to redirect to loguru
    import logging

    class InterceptHandler(logging.Handler):
        def emit(self, record):
            # Get corresponding Loguru level if it exists
            try:
                level = logger.level(record.levelname).name
            except ValueError:
                level = record.levelno

            # Find caller from where originated the logged message
            frame, depth = sys._getframe(6), 6
            while frame and frame.f_code.co_filename == logging.__file__:
                frame = frame.f_back
                depth += 1

            logger.opt(depth=depth, exception=record.exc_info).log(
                level, record.getMessage()
            )

    # Configure standard logging to use our handler
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)

    # Set level for all existing loggers to propagate to our handler
    for name in logging.root.manager.loggerDict:
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
        logging.getLogger(name).setLevel(0)

    _logging_configured = True

    logger.info(f"Logging configured at level {level.upper()}")
    if log_file:
        logger.info(f"Logging to file: {log_file}")


def get_logger(name: str | None = None):
    """
    Get a logger instance. This is just a convenience wrapper around loguru's logger.

    Args:
        name: Logger name (not used by loguru, kept for compatibility)

    Returns:
        Loguru logger instance
    """
    return logger
