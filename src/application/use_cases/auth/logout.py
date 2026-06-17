"""Use case for ending the current auth session."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import UserSessionEnded, UserTokensRevoked
from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


class LogoutUseCase(BaseUseCase[None], ApplicationEventRecorderMixin):
    """Terminate an authentication session and revoke outstanding tokens."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        auth: AuthService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository used to revoke outstanding tokens.
            auth: Authentication service containing local session state.
            clock: Clock provider used to timestamp application events.
        """
        self._user_repo = user_repository
        self._auth = auth
        self._clock = clock

        self._pending_events = []

    def execute(self, user_id: int, username: str) -> None:
        """Log out a known authenticated user.

        Args:
            user_id: Persisted user id whose outstanding tokens should be revoked.
            username: Login username to include in logout events.
        """
        occurred_at = self._clock()

        self._user_repo.increment_token_version_by_id(user_id)
        self._auth.logout()

        self._record_event(
            UserTokensRevoked(
                user_id=user_id,
                username=username,
                reason=TokenRevocationReason.USER_LOGOUT,
                occurred_at=occurred_at,
            )
        )
        self._record_event(
            UserSessionEnded(
                user_id=user_id,
                username=username,
                occurred_at=occurred_at,
            )
        )

        logger.info("Logged out user_id=%d.", user_id)

    def execute_current_session(self) -> None:
        """Log out the stateful user currently held by the auth service.

        Raises:
            PermissionError: If no local session is authenticated.
            PermissionError: If the local session has no recorded login username.
        """
        current_user = self._auth.current_user
        if current_user is None:
            raise PermissionError("Unauthenticated")

        username = self._auth.last_username
        if not isinstance(username, str) or not username.strip():
            raise PermissionError("Authenticated user has no username.")

        self.execute(user_id=current_user.user_id, username=username.strip().lower())
