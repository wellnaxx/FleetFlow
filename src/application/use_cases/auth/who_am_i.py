"""Use case for reading the current auth user."""

from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.queries.auth.who_am_i import WhoAmIQuery
from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase


class WhoAmIUseCase(BaseUseCase[CurrentUserPrincipal | None]):
    """Resolve the current principal for a fieldless identity query."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the current-principal query executor.

        Args:
            auth: Authentication service containing the current session.
        """
        self._auth = auth

    def execute(self, query: WhoAmIQuery) -> CurrentUserPrincipal | None:
        """Return the current authenticated principal.

        Args:
            query: Fieldless message selecting the principal workflow.

        Returns:
            Active current-user principal, or ``None`` when no user is logged
            in.
        """
        del query
        return self._auth.current_user
