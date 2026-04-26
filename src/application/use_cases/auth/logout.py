"""Use case for ending the current auth session."""

from src.application.services.auth_service import AuthService


class LogoutUseCase:
    """Terminate the current authentication session."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service containing the current session.
        """
        self._auth = auth

    def execute(self) -> None:
        """Log out the current user."""
        self._auth.logout()
