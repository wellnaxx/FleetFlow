"""Use case for reading the current auth user."""

from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.domain.entities.users.user import User


class WhoAmIUseCase(BaseUseCase[User | None]):
    """Return the current authenticated user, if any."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service containing the current session.
        """
        self._auth = auth

    def execute(self) -> User | None:
        """Return the current authenticated runtime user.

        Returns:
            Active user entity, or `None` when no user is logged in.
        """
        return self._auth.current_user
