from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var

logger = logging.getLogger(__name__)


class PersistenceBackend(StrEnum):
    """Supported persistence backends."""

    MEMORY = "memory"
    POSTGRES = "postgres"


@dataclass(frozen=True, slots=True)
class AppConfig:
    """Application configuration settings.

    Args:
        persistence_backend: Which persistence backend to use.
    """

    persistence_backend: PersistenceBackend


_app_config: AppConfig | None = None


def load_app_config() -> AppConfig:
    """Load application configuration from environment variables."""
    load_dotenv()

    config = AppConfig(
        persistence_backend=PersistenceBackend(get_env_var("PERSISTENCE_BACKEND", "memory")),
    )
    logger.debug("Loaded application config with persistence backend %s.", config.persistence_backend.value)
    return config


def get_app_config() -> AppConfig:
    """Return cached application config, loading it lazily on first use."""
    global _app_config

    if _app_config is None:
        _app_config = load_app_config()

    return _app_config


def set_app_config(config: AppConfig | None) -> None:
    """Override or clear application config, mainly for tests."""
    global _app_config

    _app_config = config
