"""Use case for administratively resetting another user's password."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.events.auth_events import UserPasswordReset, UserPasswordResetRejected
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.password_errors import (
    PasswordResetCriteriaNotMetError,
    PasswordResetRejectedMixin,
    PasswordResetUserNotFoundError,
)
from src.application.services.auth_normalization import normalize_username
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, record_authorization_denied
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)


class ResetPasswordUseCase(AuthorizedUseCase[None]):
    """Reset a target user's password after administrator authorization."""

    def __init__(
        self,
        auth: AuthService,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the administrative password-reset workflow.

        Args:
            auth: Authentication service used to persist replacement passwords.
            authz: Authorization state used to require administrator access.
            clock: Clock used to timestamp reset and authorization events.
        """
        super().__init__(authz)
        self._auth = auth
        self._clock = clock

    def execute(self, username: str, new_password: str) -> None:
        """Reset the target user's password.

        Args:
            username: Login name of the account to update.
            new_password: Replacement plain-text password.

        Raises:
            PermissionError: If the caller is unauthenticated or lacks
                ``ADMIN_USER`` permission.
            ValidationError: If ``username`` is blank or the new password
                fails policy validation.
            NotFoundError: If the target user does not exist.
            DatabaseError: If password persistence fails.
        """
        occurred_at = self._clock()
        normalized_username = normalize_username(username)
        if self.authz.current_user is None or not self.authz.has(Permission.ADMIN_USER):
            record_authorization_denied(
                self,
                required_permissions=(Permission.ADMIN_USER,),
                operation=AuthorizationOperation.USER_RESET_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=self._target_user_id(normalized_username),
                occurred_at=occurred_at,
            )
            if self.authz.current_user is None:
                raise PermissionError("Unauthenticated")
            raise PermissionError("Missing permission: ADMIN_USER")

        if not normalized_username:
            self._record_event(
                UserPasswordResetRejected(
                    user_id=None,
                    username=username,
                    reason=UserPasswordResetRejectionReason.INVALID_USERNAME,
                    occurred_at=occurred_at,
                )
            )
            raise ValidationError("Username must be a non-empty string.")

        try:
            record = self._auth.reset_password(normalized_username, new_password)
        except (
            PasswordResetUserNotFoundError,
            PasswordResetCriteriaNotMetError,
        ) as exc:
            self._record_password_reset_rejection(exc, occurred_at)
            raise

        self._record_event(
            UserPasswordReset(
                user_id=record.user_id,
                username=record.username,
                occurred_at=occurred_at,
            )
        )
        logger.info("Password reset completed for user %r.", normalized_username)

    def _target_user_id(self, username: str) -> int | None:
        """Return the principal id when the reset targets that same account."""
        current_user = self.authz.current_user
        if current_user is None:
            return None
        current_username = normalize_username(current_user.username)
        return current_user.user_id if current_username == username else None

    def _record_password_reset_rejection(
        self,
        exc: PasswordResetRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        """Record a typed password-reset rejection.

        Args:
            exc: Authentication-service failure carrying audit metadata.
            occurred_at: Business timestamp shared by the attempted workflow.
        """
        self._record_event(
            UserPasswordResetRejected(
                user_id=exc.user_id,
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )
