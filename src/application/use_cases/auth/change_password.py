"""Use case for changing the current authenticated user's password."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.events.auth_events import UserPasswordChanged, UserPasswordChangeRejected
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.password_errors import (
    CurrentPasswordIncorrectError,
    InvalidPersistedPasswordHashError,
    PasswordChangeCriteriaNotMetError,
    PasswordChangeRejectedMixin,
    PasswordChangeUserNotFoundError,
    PasswordUnchangedError,
)
from src.application.services.auth_normalization import normalize_username
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, record_authorization_denied
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission

logger = logging.getLogger(__name__)


class ChangePasswordUseCase(AuthorizedUseCase[None]):
    """Change the authenticated principal's password after verification."""

    def __init__(
        self,
        auth: AuthService,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the self-service password-change workflow.

        Args:
            auth: Authentication service used to verify and update passwords.
            authz: Authorization state containing the current principal.
            clock: Clock used to timestamp password and authorization events.
        """
        super().__init__(authz)
        self._auth = auth
        self._clock = clock

    def execute(self, current_password: str, new_password: str) -> None:
        """Change the current principal's password.

        Args:
            current_password: Existing plain-text password to verify.
            new_password: Replacement plain-text password.

        Raises:
            PermissionError: If no user is authenticated.
            ValidationError: If the principal username or password data is
                invalid, the replacement fails policy, or it matches the
                existing password.
            NotFoundError: If the authenticated user no longer exists.
            AuthenticationError: If ``current_password`` is incorrect.
            DatabaseError: If password persistence fails.
        """
        occurred_at = self._clock()
        current_user = self.authz.current_user

        if current_user is None:
            record_authorization_denied(
                self,
                required_permissions=(Permission.AUTHENTICATED,),
                operation=AuthorizationOperation.USER_CHANGE_PASSWORD,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=None,
                occurred_at=occurred_at,
            )
            raise PermissionError("Unauthenticated")

        username = current_user.username
        normalized_username = normalize_username(username)
        if not normalized_username:
            self._record_event(
                UserPasswordChangeRejected(
                    user_id=current_user.user_id,
                    username=username,
                    reason=UserPasswordChangeRejectionReason.INVALID_USERNAME,
                    occurred_at=occurred_at,
                )
            )
            raise ValidationError("Username must be a non-empty string.")

        try:
            record = self._auth.change_password(
                normalized_username,
                current_password,
                new_password,
            )
        except (
            PasswordChangeUserNotFoundError,
            InvalidPersistedPasswordHashError,
            CurrentPasswordIncorrectError,
            PasswordUnchangedError,
            PasswordChangeCriteriaNotMetError,
        ) as exc:
            self._record_password_change_rejection(exc, occurred_at)
            raise

        self._record_event(
            UserPasswordChanged(
                user_id=record.user_id,
                username=record.username,
                occurred_at=occurred_at,
            )
        )
        logger.info("Password changed for current user %r.", normalized_username)

    def _record_password_change_rejection(
        self,
        exc: PasswordChangeRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        """Record a typed password-change rejection.

        Args:
            exc: Authentication-service failure carrying audit metadata.
            occurred_at: Business timestamp shared by the attempted workflow.
        """
        self._record_event(
            UserPasswordChangeRejected(
                user_id=exc.user_id,
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )
