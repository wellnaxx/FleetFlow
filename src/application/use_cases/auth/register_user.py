"""Use case for registering a new user."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.events.auth_events import UserRegistered, UserRegistrationRejected
from src.application.exceptions.password_errors import (
    RegistrationInvalidUsernameError,
    RegistrationPasswordCriteriaNotMetError,
    RegistrationRejectedMixin,
    RegistrationUsernameAlreadyExistsError,
)
from src.application.models.user_record import UserRecord
from src.application.services.auth_normalization import normalize_username
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission, Role

if TYPE_CHECKING:
    from collections.abc import Callable

    from src.application.commands.auth.register_user import RegisterUserCommand
    from src.application.services.auth_service import AuthService

logger = logging.getLogger(__name__)


def _username_resource_id(
    _self: RegisterUserUseCase,
    command: RegisterUserCommand,
) -> str | None:
    """Resolve the normalized username targeted by a registration command.

    Args:
        _self: Decorated registration use case. Unused because the target is
            carried entirely by the command.
        command: Registration request whose username identifies the target.

    Returns:
        Normalized username, or ``None`` when normalization produces an empty
        value.
    """
    return normalize_username(command.username) or None


class RegisterUserUseCase(AuthorizedUseCase[UserRecord]):
    """Register a new user through the auth service."""

    def __init__(
        self,
        auth: AuthService,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to create users.
            authz: Service used for authorization checks.
            clock: Clock provider used to timestamp application events.
        """
        super().__init__(authz)
        self._auth = auth
        self._clock = clock

    @requires(
        Permission.ADMIN_USER,
        operation=AuthorizationOperation.USER_REGISTER,
        target_resource_type=AuditResourceType.USER,
        target_resource_id_resolver=_username_resource_id,
    )
    def execute(self, command: RegisterUserCommand) -> UserRecord:
        """Register a new user account.

        Args:
            command: Account identity, profile, role, and initial password.

        Returns:
            The persisted user record.

        Raises:
            PermissionError: If the caller lacks admin-user permission.
            RegistrationInvalidUsernameError: If the username or repository input is invalid.
            RegistrationUsernameAlreadyExistsError: If the username already exists.
            RegistrationPasswordCriteriaNotMetError: If the password fails validation.
        """
        occurred_at = self._clock()

        try:
            record = self._auth.register_user(
                username=command.username,
                role=command.role,
                name=command.name,
                email=command.email,
                phone_number=command.phone_number,
                password=command.password,
            )
        except (
            RegistrationInvalidUsernameError,
            RegistrationUsernameAlreadyExistsError,
            RegistrationPasswordCriteriaNotMetError,
        ) as exc:
            self._record_registration_rejection(exc, occurred_at)
            raise
        else:
            self.record_event(
                UserRegistered(
                    user_id=record.user_id,
                    username=record.username,
                    role=Role(record.role),
                    occurred_at=occurred_at,
                )
            )

        logger.info("Registered user %r with role %s.", record.username, record.role)

        return record

    def _record_registration_rejection(
        self,
        exc: RegistrationRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        """Record the typed failure metadata carried by a registration error.

        Args:
            exc: Registration failure containing the normalized username and
                rejection reason safe for audit publication.
            occurred_at: Business timestamp shared by the attempted workflow.
        """
        self.record_event(
            UserRegistrationRejected(
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )
