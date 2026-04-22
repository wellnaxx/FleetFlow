from src.application.services.auth_service import AuthService


class ChangePasswordUseCase:
    """Change or reset a user's password through the auth service."""

    def __init__(self, auth: AuthService) -> None:
        self._auth = auth

    def execute(self, username: str, new_password: str, old_password: str | None = None) -> None:
        """Change a password, optionally verifying the old password first.

        Args:
            username: Username whose password should change.
            new_password: Replacement plain-text password.
            old_password: Existing password required for a regular password
                change. When omitted, the flow becomes a reset.

        Raises:
            ValueError: If the user is missing or the password change is invalid.
        """
        if old_password is None:
            self._auth.reset_password(username, new_password)
            return
        self._auth.change_password(username, old_password, new_password)
