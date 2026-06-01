import logging
from functools import lru_cache

from src.adapters.driven.persistence.database.repositories.user_repository import PostgresUserRepository
from src.adapters.driven.persistence.json.config import get_json_config
from src.adapters.driven.persistence.json.user_store import JSONUserStore
from src.application.services.auth_service import AuthService
from src.composition.config import PersistenceBackend, get_app_config
from src.composition.container import Container, build_container
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_user_repository() -> UserRepositoryPort:
    """Get the application's user repository instance.

    Returns:
        The user repository for the configured persistence backend. Memory mode
        uses the local JSON user store; Postgres mode uses the Postgres user
        repository.

    Raises:
        ValueError: If the configured persistence backend is unsupported.
    """
    config = get_app_config()
    if config.persistence_backend is PersistenceBackend.MEMORY:
        logger.info("Using JSON user repository for memory backend.")
        return JSONUserStore(str(get_json_config().user_store_path))
    if config.persistence_backend is PersistenceBackend.POSTGRES:
        logger.info("Using PostgreSQL user repository.")
        return PostgresUserRepository()

    logger.critical("Unsupported persistence backend configured: %r.", config.persistence_backend)
    raise ValueError(f"Unsupported persistence backend: {config.persistence_backend!r}")


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    """Get the application's AuthService instance.

    Returns:
        The AuthService instance used by the application.
    """
    logger.debug("Creating shared AuthService instance.")
    return AuthService(get_user_repository())


@lru_cache(maxsize=1)
def get_container() -> Container:
    """Get the application's dependency injection container.

    Returns:
        The Container instance used by the application.
    """
    logger.info("Building shared application container.")
    return build_container(get_auth_service(), get_app_config())
