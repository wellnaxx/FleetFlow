"""Use case for changing an authenticated user's password."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.events.auth_events import (
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
)
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.password_errors import (
    CurrentPasswordIncorrectError,
    InvalidPersistedPasswordHashError,
    PasswordChangeCriteriaNotMetError,
    PasswordChangeRejectedMixin,
    PasswordChangeUserNotFoundError,
    PasswordResetCriteriaNotMetError,
    PasswordResetRejectedMixin,
    PasswordResetUserNotFoundError,
    PasswordUnchangedError,
)
from src.application.services.auth_normalization import normalize_username
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, record_authorization_denied
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)


class ChangePasswordUseCase(AuthorizedUseCase[None]):
    """Coordinate authenticated password changes and admin password resets."""

    def __init__(
        self,
        auth: AuthService,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to update passwords.
            authz: Service used for authorization checks.
            clock: Clock provider used to timestamp application events.
        """
        super().__init__(authz)
        self._auth = auth
        self._clock = clock

    def execute(self, username: str, new_password: str, old_password: str | None = None) -> None:
        """Change a password, optionally verifying the old password first.

        Args:
            username: Username whose password should change.
            new_password: Replacement plain-text password.
            old_password: Existing password required for a regular password
                change. When omitted, the flow becomes a reset.

        Raises:
            PermissionError: If the caller is not authorized to perform the action.
            ValidationError: If the username is invalid, persisted password
                data is invalid, password validation fails, or the new
                password matches the old one.
            NotFoundError: If the target user is missing.
            AuthenticationError: If the old password is wrong.
        """
        occurred_at = self._clock()

        try:
            target_username = self._normalize_username(username)
        except ValidationError:
            if old_password is None:
                self._record_event(
                    UserPasswordResetRejected(
                        user_id=None,
                        username=username,
                        reason=UserPasswordResetRejectionReason.INVALID_USERNAME,
                        occurred_at=occurred_at,
                    )
                )
            else:
                self._record_event(
                    UserPasswordChangeRejected(
                        user_id=None,
                        username=username,
                        reason=UserPasswordChangeRejectionReason.INVALID_USERNAME,
                        occurred_at=occurred_at,
                    )
                )
            raise

        if old_password is None:
            try:
                self._require_admin()
            except PermissionError:
                record_authorization_denied(
                    self,
                    required_permissions=(Permission.ADMIN_USER,),
                    operation=AuthorizationOperation.USER_RESET_PASSWORD,
                    target_resource_type=AuditResourceType.USER,
                    target_resource_id=self._target_user_id(target_username),
                    occurred_at=occurred_at,
                )
                raise
            try:
                record = self._auth.reset_password(target_username, new_password)
            except (
                PasswordResetUserNotFoundError,
                PasswordResetCriteriaNotMetError,
            ) as exc:
                self._record_password_reset_rejection(exc, occurred_at)
                raise
            else:
                self._record_event(
                    UserPasswordReset(
                        user_id=record.user_id,
                        username=record.username,
                        occurred_at=occurred_at,
                    )
                )
                self._log_password_updated("Password reset completed", target_username)
            return

        try:
            self._require_authenticated()
        except PermissionError:
            record_authorization_denied(
                self,
                required_permissions=(Permission.AUTHENTICATED,),
                operation=AuthorizationOperation.USER_CHANGE_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=self._target_user_id(target_username),
                occurred_at=occurred_at,
            )
            raise

        if not self._is_current_user(target_username) and not self.authz.has(Permission.ADMIN_USER):
            record_authorization_denied(
                self,
                required_permissions=(Permission.ADMIN_USER,),
                operation=AuthorizationOperation.USER_CHANGE_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=self._target_user_id(target_username),
                occurred_at=occurred_at,
            )
            raise PermissionError("Cannot change another user's password.")

        try:
            record = self._auth.change_password(target_username, old_password, new_password)
        except (
            PasswordChangeUserNotFoundError,
            InvalidPersistedPasswordHashError,
            CurrentPasswordIncorrectError,
            PasswordUnchangedError,
            PasswordChangeCriteriaNotMetError,
        ) as exc:
            self._record_password_change_rejection(exc, occurred_at)
            raise
        else:
            self._record_event(
                UserPasswordChanged(
                    user_id=record.user_id,
                    username=record.username,
                    occurred_at=occurred_at,
                )
            )
            self._log_password_updated("Password changed", target_username)

    def execute_current_user(self, new_password: str, old_password: str) -> None:
        """Change the currently authenticated user's password.

        Args:
            new_password: Replacement plain-text password.
            old_password: Existing password required for verification.

        Raises:
            PermissionError: If no user is authenticated.
            ValidationError: If the username is invalid, persisted password
                data is invalid, password validation fails, or the new
                password matches the old one.
            NotFoundError: If the target user is missing.
            AuthenticationError: If the old password is wrong.
        """
        occurred_at = self._clock()
        current_user = self.authz.current_user
        username = current_user.username if current_user is not None else None

        try:
            self._require_authenticated()
        except PermissionError:
            record_authorization_denied(
                self,
                required_permissions=(Permission.AUTHENTICATED,),
                operation=AuthorizationOperation.USER_CHANGE_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=self._current_user_id(),
                occurred_at=occurred_at,
            )
            raise

        current_user = self.authz.current_user
        assert current_user is not None
        username = current_user.username

        try:
            current_username = self._normalize_username(username)
        except ValidationError:
            self._record_event(
                UserPasswordChangeRejected(
                    user_id=None,
                    username=username,
                    reason=UserPasswordChangeRejectionReason.INVALID_USERNAME,
                    occurred_at=occurred_at,
                )
            )
            raise

        if not self._is_current_user(current_username):
            record_authorization_denied(
                self,
                required_permissions=(Permission.ADMIN_USER,),
                operation=AuthorizationOperation.USER_CHANGE_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=self._current_user_id(),
                occurred_at=occurred_at,
            )
            raise PermissionError("Username does not match authenticated user.")

        try:
            record = self._auth.change_password(current_username, old_password, new_password)
        except (
            PasswordChangeUserNotFoundError,
            InvalidPersistedPasswordHashError,
            CurrentPasswordIncorrectError,
            PasswordUnchangedError,
            PasswordChangeCriteriaNotMetError,
        ) as exc:
            self._record_password_change_rejection(exc, occurred_at)
            raise
        else:
            self._record_event(
                UserPasswordChanged(
                    user_id=record.user_id,
                    username=record.username,
                    occurred_at=occurred_at,
                )
            )
            self._log_password_updated("Password changed for current user", current_username)

    @property
    def current_session_username(self) -> str | None:
        """Return the username from the current authenticated principal."""
        return self._current_username()

    def _current_username(self) -> str | None:
        """Return the authenticated username from authorization state."""
        current_user = self.authz.current_user
        if current_user is None:
            return None

        return normalize_username(current_user.username) or None

    def _current_user_id(self) -> int | None:
        """Return the authenticated principal user id, if any."""
        current_user = self.authz.current_user
        return current_user.user_id if current_user is not None else None

    def _target_user_id(self, username: str) -> int | None:
        """Return the canonical id when the target is the current user."""
        return self._current_user_id() if self._is_current_user(username) else None

    def _require_authenticated(self) -> None:
        if self.authz.current_user is None:
            raise PermissionError("Unauthenticated")

    def _require_admin(self) -> None:
        self._require_authenticated()
        if not self.authz.has(Permission.ADMIN_USER):
            raise PermissionError("Missing permission: ADMIN_USER")

    def _normalize_username(self, username: str) -> str:
        normalized = normalize_username(username)
        if not normalized:
            raise ValidationError("Username must be a non-empty string.")
        return normalized

    def _is_current_user(self, username: str) -> bool:
        current_username = self._current_username()
        return current_username is not None and username == current_username

    def _record_password_change_rejection(
        self,
        exc: PasswordChangeRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        self._record_event(
            UserPasswordChangeRejected(
                user_id=exc.user_id,
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )

    def _record_password_reset_rejection(
        self,
        exc: PasswordResetRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        self._record_event(
            UserPasswordResetRejected(
                user_id=exc.user_id,
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )

    def _log_password_updated(self, message: str, username: str) -> None:
        logger.info("%s for user %r.", message, username)
