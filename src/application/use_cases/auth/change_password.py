"""Use case for changing an authenticated user's password."""

from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission


class ChangePasswordUseCase(AuthorizedUseCase[None]):
    """Change or reset a user's password through the auth service."""

    def __init__(self, auth: AuthService, authz: AuthorizationService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to update passwords.
            authz: Service used for authorization checks.
        """
        super().__init__(authz)
        self._auth = auth

    def execute(self, username: str, new_password: str, old_password: str | None = None) -> None:
        """Change a password, optionally verifying the old password first.

        Args:
            username: Username whose password should change.
            new_password: Replacement plain-text password.
            old_password: Existing password required for a regular password
                change. When omitted, the flow becomes a reset.

        Raises:
            NotFoundError: If the user is missing.
            AuthenticationError: If the old password is wrong.
            ValidationError: If password validation fails.
            PermissionError: If the caller is not authorized to perform the action.
        """
        if old_password is None:
            if self.authz.current_user is None:
                raise PermissionError("Unauthenticated")
            if not self.authz.has(Permission.ADMIN_USER):
                raise PermissionError("Missing permission: ADMIN_USER")
            self._auth.reset_password(username, new_password)
            return

        if self.authz.current_user is None:
            raise PermissionError("Unauthenticated")

        current_username = self._current_username()
        is_self_change = current_username is not None and username.strip().lower() == current_username
        if not is_self_change and not self.authz.has(Permission.ADMIN_USER):
            raise PermissionError("Cannot change another user's password.")

        self._auth.change_password(username, old_password, new_password)

    @property
    def current_session_username(self) -> str | None:
        """Return the username recorded by a session-oriented auth service."""
        return self._current_username()

    def execute_current_user(self, username: str | None, new_password: str, old_password: str) -> None:
        """Change the currently authenticated user's password.

        Args:
            username: Authenticated username supplied by the driving adapter.
            new_password: Replacement plain-text password.
            old_password: Existing password required for verification.

        Raises:
            PermissionError: If no user is authenticated.
            PermissionError: If the driving adapter does not provide a username.
            AuthenticationError: If the old password is wrong.
            NotFoundError: If the user is missing.
            ValidationError: If password validation fails.
        """
        if self.authz.current_user is None:
            raise PermissionError("Unauthenticated")

        if not isinstance(username, str) or not username.strip():
            raise PermissionError("Authenticated user has no username.")

        self._auth.change_password(username.strip().lower(), old_password, new_password)

    def _current_username(self) -> str | None:
        """Return the authenticated username from auth session state."""
        if self.authz.current_user is None:
            return None

        last_username = self._auth.last_username
        if isinstance(last_username, str) and last_username.strip():
            return last_username.strip().lower()

        return None
