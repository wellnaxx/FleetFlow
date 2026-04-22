from src.application.services.auth_service import AuthService
from src.domain.entities.users.user import User


class WhoAmIUseCase:
    """Return the current authenticated user, if any."""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self) -> User | None:
        """Return the current authenticated runtime user."""
        return self._auth.current_user
