"""
SynapseOps Structured Logging.

Configures structlog for JSON-compatible structured output.
All application code should use the logger returned by get_logger().
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO", *, json_logs: bool = False) -> None:
    """Configure structlog for the application.

    Args:
        log_level: The minimum log level to emit (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        json_logs: If True, emit JSON-formatted logs (recommended for production).
                   If False, emit human-readable colored logs (useful in development).
    """
    log_level_int = getattr(logging, log_level.upper(), logging.INFO)

    # Configure stdlib logging so SQLAlchemy, uvicorn, etc. are captured
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level_int,
    )

    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if json_logs:
        # Production: structured JSON output for log aggregation tools
        processors = [
            *shared_processors,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ]
    else:
        # Development: human-readable colored output
        processors = [
            *shared_processors,
            structlog.processors.ExceptionRenderer(),
            structlog.dev.ConsoleRenderer(colors=True),
        ]

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level_int),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )


def get_logger(component: str) -> structlog.BoundLogger:
    """Return a bound logger with the component name pre-bound.

    Args:
        component: Logical name of the component emitting the log.
                   Examples: "api.health", "db.session", "cache.redis"

    Returns:
        A structlog BoundLogger with 'component' pre-bound as a context field.

    Example:
        logger = get_logger("api.health")
        logger.info("Health check requested")
        # Emits: {"component": "api.health", "event": "Health check requested", ...}
    """
    return structlog.get_logger().bind(component=component)
