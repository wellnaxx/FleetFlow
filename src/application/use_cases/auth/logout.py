"""Use case for ending the current auth session."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import AuthorizationDenied, UserSessionEnded, UserTokensRevoked
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.domain.enums.auth import Permission
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


class LogoutUseCase(BaseUseCase[None], ApplicationEventRecorderMixin):
    """Terminate an authentication session and revoke outstanding tokens."""

    def __init__(
        self,
        user_repository: UserRepositoryPort,
        auth: AuthService,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the use case.

        Args:
            user_repository: Repository used to revoke outstanding tokens.
            auth: Authentication service containing local session state.
            authz: Request or session authorization state containing the current principal.
            clock: Clock provider used to timestamp application events.
        """
        self._user_repo = user_repository
        self._auth = auth
        self._authz = authz
        self._clock = clock

        self._pending_events = []

    def execute(self) -> None:
        """Log out the current authenticated principal.

        Raises:
            PermissionError: If no principal is authenticated or the principal
                has no username.
        """
        occurred_at = self._clock()

        current_user = self._authz.current_user
        if current_user is None:
            self._record_event(
                AuthorizationDenied(
                    user_id=None,
                    username=None,
                    required_permissions=(Permission.AUTHENTICATED,),
                    occurred_at=occurred_at,
                )
            )
            raise PermissionError("Unauthenticated")

        username = current_user.username
        if not username.strip():
            self._record_event(
                AuthorizationDenied(
                    user_id=current_user.user_id,
                    username=username,
                    required_permissions=(Permission.AUTHENTICATED,),
                    occurred_at=occurred_at,
                )
            )
            raise PermissionError("Authenticated user has no username.")

        self._user_repo.increment_token_version_by_id(current_user.user_id)
        self._auth.logout()

        self._record_event(
            UserTokensRevoked(
                user_id=current_user.user_id,
                username=username,
                reason=TokenRevocationReason.USER_LOGOUT,
                occurred_at=occurred_at,
            )
        )
        self._record_event(
            UserSessionEnded(
                user_id=current_user.user_id,
                username=username,
                occurred_at=occurred_at,
            )
        )

        logger.info("Logged out user_id=%d.", current_user.user_id)
