"""Use case for authenticating a user."""

import logging

from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.domain.entities.users.user import User

logger = logging.getLogger(__name__)


class LoginUseCase(BaseUseCase[User]):
    """Authenticate a user through the auth service."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to verify credentials.
        """
        self._auth = auth

    def execute(self, username: str, password: str) -> User:
        """Authenticate a user and return the runtime user entity.

        Args:
            username: Login username.
            password: Plain-text password.

        Returns:
            The authenticated runtime user entity.

        Raises:
            AuthenticationError: If the credentials are invalid.
            ValidationError: If persisted user data is invalid.
        """
        user = self._auth.login(username, password)
        logger.info("User %r authenticated.", username.strip().lower())
        return user
