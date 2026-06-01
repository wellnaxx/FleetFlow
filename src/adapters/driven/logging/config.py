"""Standard logging configuration for FleetFlow."""

import logging
import logging.handlers
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var

_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
_LOG_LEVELS = {
    "CRITICAL": logging.CRITICAL,
    "ERROR": logging.ERROR,
    "WARNING": logging.WARNING,
    "INFO": logging.INFO,
    "DEBUG": logging.DEBUG,
    "NOTSET": logging.NOTSET,
}


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration loaded from the environment.

    Attributes:
        level: Minimum log level to emit.
        log_file: Optional path to write logs to in addition to stdout.
    """

    level: int
    log_file: Path | None


def load_logging_config() -> LoggingConfig:
    """Load logging configuration from environment variables.

    Returns:
        LoggingConfig populated from LOG_LEVEL and LOG_FILE environment variables.
    """
    load_dotenv()

    raw_level = get_env_var("LOG_LEVEL", "INFO").strip().upper()
    try:
        level = _LOG_LEVELS[raw_level]
    except KeyError as exc:
        supported = ", ".join(_LOG_LEVELS)
        raise ValueError(f"Unsupported LOG_LEVEL: {raw_level}. Supported values: {supported}.") from exc

    raw_file = get_env_var("LOG_FILE", "").strip()
    log_file = Path(raw_file) if raw_file else None

    return LoggingConfig(level=level, log_file=log_file)


def configure_logging(config: LoggingConfig | None = None) -> None:
    """Configure the root logger for the FleetFlow application.

    Args:
        config: Logging configuration. When omitted, loaded from the environment.
    """
    config = config or load_logging_config()

    formatter = logging.Formatter(fmt=_FORMAT, datefmt=_DATE_FORMAT)

    handlers: list[logging.Handler] = [
        logging.StreamHandler(sys.stdout),
    ]

    if config.log_file is not None:
        config.log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=config.log_file,
            maxBytes=10 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        handlers.append(file_handler)

    for handler in handlers:
        handler.setFormatter(formatter)

    logging.basicConfig(
        level=config.level,
        handlers=handlers,
        force=True,
    )

    # Suppress noisy third-party loggers.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
    logging.getLogger("multipart").setLevel(logging.WARNING)
