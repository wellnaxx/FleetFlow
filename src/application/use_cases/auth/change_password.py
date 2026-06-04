"""Use case for changing an authenticated user's password."""

import logging

from src.application.exceptions.application_errors import ValidationError
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)


class ChangePasswordUseCase(AuthorizedUseCase[None]):
    """Coordinate authenticated password changes and admin password resets."""

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
        target_username = self._normalize_username(username)

        if old_password is None:
            self._require_admin()
            self._auth.reset_password(target_username, new_password)
            self._log_password_updated("Password reset completed", target_username)
            return

        self._require_authenticated()

        if not self._is_current_user(target_username) and not self.authz.has(Permission.ADMIN_USER):
            raise PermissionError("Cannot change another user's password.")

        self._auth.change_password(target_username, old_password, new_password)
        self._log_password_updated("Password changed", target_username)

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
        self._require_authenticated()

        if username is None:
            raise PermissionError("Authenticated user has no username.")

        current_username = self._normalize_username(username)
        if not self._is_current_user(current_username):
            raise PermissionError("Username does not match authenticated user.")

        self._auth.change_password(current_username, old_password, new_password)
        self._log_password_updated("Password changed for current user", current_username)

    @property
    def current_session_username(self) -> str | None:
        """Return the username recorded by a session-oriented auth service."""
        return self._current_username()

    def _current_username(self) -> str | None:
        """Return the authenticated username from auth session state."""
        if self.authz.current_user is None:
            return None

        last_username = self._auth.last_username
        return (
            last_username.strip().lower() if isinstance(last_username, str) and last_username.strip() else None
        )

    def _require_authenticated(self) -> None:
        if self.authz.current_user is None:
            raise PermissionError("Unauthenticated")

    def _require_admin(self) -> None:
        self._require_authenticated()
        if not self.authz.has(Permission.ADMIN_USER):
            raise PermissionError("Missing permission: ADMIN_USER")

    def _normalize_username(self, username: str) -> str:
        normalized = username.strip().lower()
        if not normalized:
            raise ValidationError("Username must be a non-empty string.")
        return normalized

    def _is_current_user(self, username: str) -> bool:
        current_username = self._current_username()
        return current_username is not None and username == current_username

    def _log_password_updated(self, message: str, username: str) -> None:
        logger.info("%s for user %r.", message, username)
