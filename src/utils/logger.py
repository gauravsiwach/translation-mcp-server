import logging
import structlog
from config import settings

def configure_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logging.basicConfig(level=level, format="%(message)s")

    processors = [
        structlog.threadlocal.merge_threadlocal,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.APP_ENV.lower() == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def configure_logging_with_file(log_file_path: str = None):
    """Configure structlog to write to both file and console.
    
    Args:
        log_file_path: Optional path to log file. If provided, logs will be written to this file.
                      If None, logs only go to console.
    """
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    
    # Get root logger and clear existing handlers
    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    
    # Setup handlers
    handlers = [logging.StreamHandler()]  # Always write to console
    
    if log_file_path:
        file_handler = logging.FileHandler(log_file_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(logging.Formatter("%(message)s"))
        handlers.append(file_handler)
    
    # Add handlers to root logger
    for handler in handlers:
        handler.setLevel(level)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root_logger.addHandler(handler)
    
    # Configure structlog processors
    processors = [
        structlog.threadlocal.merge_threadlocal,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    
    if settings.APP_ENV.lower() == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())
    
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=False,  # Disable cache to allow reconfiguration
    )


# configure on import
configure_logging()


def get_logger(name: str = None):
    return structlog.get_logger(name)
