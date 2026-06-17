"""Use case for registering a new user."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.events.auth_events import UserRegistered, UserRegistrationRejected
from src.application.exceptions.password_errors import (
    RegistrationInvalidUsernameError,
    RegistrationPasswordCriteriaNotMetError,
    RegistrationRejectedMixin,
    RegistrationUsernameAlreadyExistsError,
)
from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.enums.auth import Permission, Role

logger = logging.getLogger(__name__)


class RegisterUserUseCase(AuthorizedUseCase[UserRecord], ApplicationEventRecorderMixin):
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

        self._pending_events = []

    @requires(Permission.ADMIN_USER)
    def execute(
        self,
        username: str,
        role: Role,
        name: str,
        email: str,
        phone_number: str,
        password: str,
    ) -> UserRecord:
        """Register a new user account.

        Args:
            username: Unique login name.
            role: Role assigned to the new user.
            name: Human-readable display name.
            email: Optional email address.
            phone_number: Optional phone number.
            password: Plain-text password to hash before storage.

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
                username=username,
                role=role,
                name=name,
                email=email,
                phone_number=phone_number,
                password=password,
            )
        except (
            RegistrationInvalidUsernameError,
            RegistrationUsernameAlreadyExistsError,
            RegistrationPasswordCriteriaNotMetError,
        ) as exc:
            self._record_registration_rejection(exc, occurred_at)
            raise
        else:
            self._record_event(
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
        self._record_event(
            UserRegistrationRejected(
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )
