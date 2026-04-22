from src.application.services.auth_service import AuthService
from src.domain.entities.users.user import User


class LoginUseCase:
    """Authenticate a user through the auth service."""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self, username: str, password: str) -> User:
        """Authenticate a user and return the runtime user entity.

        Args:
            username: Login username.
            password: Plain-text password.

        Returns:
            The authenticated runtime user entity.

        Raises:
            ValueError: If the credentials are invalid.
        """
        return self._auth.login(username, password)
