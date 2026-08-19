"""Use case for authenticating a user."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.commands.auth.login import LoginCommand
from src.application.events.auth_events import UserAuthenticated, UserLoginRejected
from src.application.exceptions.password_errors import (
    LoginInvalidPersistedPasswordHashError,
    LoginInvalidUserRuntimeError,
    LoginRejectedMixin,
    LoginUserNotFoundError,
    LoginWrongPasswordError,
)
from src.application.results.login_result import LoginResult
from src.application.services.auth_normalization import normalize_username
from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin

logger = logging.getLogger(__name__)


class LoginUseCase(BaseUseCase[LoginResult], ApplicationEventRecorderMixin):
    """Authenticate a user through the auth service."""

    def __init__(self, auth: AuthService, clock: Callable[[], datetime] = datetime.now) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service used to verify credentials.
            clock: Clock provider used to timestamp application events.
        """
        self._auth = auth
        self._clock = clock

        self._pending_events = []

    def execute(self, command: LoginCommand) -> LoginResult:
        """Authenticate a user and return persisted record plus current principal.

        Args:
            command: Login name and plain-text password supplied by the
                unauthenticated caller.

        Returns:
            Login result containing the persisted user record and authenticated principal.

        Raises:
            AuthenticationError: If the username is unknown or password is invalid.
            ValidationError: If persisted user data is invalid.
        """
        occurred_at = self._clock()

        try:
            principal, record = self._auth.login(command.username, command.password)
        except (
            LoginUserNotFoundError,
            LoginInvalidPersistedPasswordHashError,
            LoginWrongPasswordError,
            LoginInvalidUserRuntimeError,
        ) as exc:
            self._record_login_rejection(exc, occurred_at)
            raise
        else:
            self.record_event(
                UserAuthenticated(
                    user_id=principal.user_id,
                    username=principal.username,
                    role=principal.role,
                    occurred_at=occurred_at,
                )
            )

        logger.info("User %r authenticated.", normalize_username(command.username))
        return LoginResult(record, principal)

    def _record_login_rejection(
        self,
        exc: LoginRejectedMixin,
        occurred_at: datetime,
    ) -> None:
        """Record a typed authentication rejection event.

        Args:
            exc: Authentication failure carrying normalized audit metadata.
            occurred_at: Business timestamp shared by the login attempt.
        """
        self.record_event(
            UserLoginRejected(
                user_id=exc.user_id,
                username=exc.username,
                reason=exc.reason,
                occurred_at=occurred_at,
            )
        )
