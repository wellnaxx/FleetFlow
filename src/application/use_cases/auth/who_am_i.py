"""Use case for reading the current auth user."""

from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase


class WhoAmIUseCase(BaseUseCase[CurrentUserPrincipal | None]):
    """Return the current authenticated user, if any."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service containing the current session.
        """
        self._auth = auth

    def execute(self) -> CurrentUserPrincipal | None:
        """Return the current authenticated principal.

        Returns:
            Active current-user principal, or `None` when no user is logged in.
        """
        return self._auth.current_user
