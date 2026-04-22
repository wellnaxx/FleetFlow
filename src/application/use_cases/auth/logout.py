from src.application.services.auth_service import AuthService


class LogoutUseCase:
    """Terminate the current authentication session."""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self) -> None:
        """Log out the current user."""
        self._auth.logout()
