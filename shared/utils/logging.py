import logging
import sys
from typing import Any

import structlog

from shared.config.settings import get_settings


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        s = get_settings()
        record.env = s.env.value
        record.service_name = s.service_name
        record.strategy_version = s.strategy_version
        record.model_version = s.model_version
        record.config_version = s.config_version
        return True


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))
    handler.addFilter(ContextFilter())
    root.handlers = [handler]

    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", key="timestamp"),
            structlog.processors.add_log_level,
            structlog.processors.EventRenamer("message"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def get_logger(**kwargs: Any) -> structlog.BoundLogger:
    return structlog.get_logger().bind(**kwargs)
