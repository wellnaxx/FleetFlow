from functools import lru_cache

from src.adapters.driven.persistence.json.config import get_json_config
from src.adapters.driven.persistence.json.user_store import JSONUserStore
from src.application.services.auth_service import AuthService
from src.composition.config import load_app_config
from src.composition.container import Container, build_container
from src.ports.output.user_repository import UserRepositoryPort


@lru_cache(maxsize=1)
def get_user_repository() -> UserRepositoryPort:
    """Get the application's user repository instance.

    Returns:
        The user repository used by authentication and HTTP token validation.
    """
    return JSONUserStore(str(get_json_config().user_store_path))


@lru_cache(maxsize=1)
def get_auth_service() -> AuthService:
    """Get the application's AuthService instance.

    Returns:
        The AuthService instance used by the application.
    """
    return AuthService(get_user_repository())


@lru_cache(maxsize=1)
def get_container() -> Container:
    """Get the application's dependency injection container.

    Returns:
        The Container instance used by the application.
    """
    return build_container(get_auth_service(), load_app_config())
