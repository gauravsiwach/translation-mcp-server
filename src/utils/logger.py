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


# configure on import
configure_logging()


def get_logger(name: str = None):
    return structlog.get_logger(name)
