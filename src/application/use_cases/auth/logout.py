"""Use case for ending the current auth session."""

import logging
from collections.abc import Callable
from datetime import datetime

from src.application.commands.auth.logout import LogoutCommand
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.events.auth_events import UserSessionEnded, UserTokensRevoked
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService, record_authorization_denied
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.ports.output.user_repository import UserRepositoryPort

logger = logging.getLogger(__name__)


class LogoutUseCase(AuthorizedUseCase[None]):
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
        super().__init__(authz)
        self._user_repo = user_repository
        self._auth = auth
        self._clock = clock

    def execute(self, command: LogoutCommand) -> None:
        """Log out the current authenticated principal.

        Args:
            command: Fieldless command selecting the context-driven logout
                workflow.

        Raises:
            PermissionError: If no principal is authenticated or the principal
                has no username.
            DatabaseError: If token-version persistence fails.
        """
        occurred_at = self._clock()
        del command

        current_user = self.authz.current_user
        if current_user is None:
            record_authorization_denied(
                self,
                required_permissions=(Permission.AUTHENTICATED,),
                operation=AuthorizationOperation.SESSION_END,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=None,
                occurred_at=occurred_at,
            )
            raise PermissionError("Unauthenticated")

        username = current_user.username
        if not username.strip():
            record_authorization_denied(
                self,
                required_permissions=(Permission.AUTHENTICATED,),
                operation=AuthorizationOperation.SESSION_END,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=current_user.user_id,
                occurred_at=occurred_at,
            )
            raise PermissionError("Authenticated user has no username.")

        self._user_repo.increment_token_version_by_id(current_user.user_id)
        self._auth.logout()

        self.record_event(
            UserTokensRevoked(
                user_id=current_user.user_id,
                username=username,
                reason=TokenRevocationReason.USER_LOGOUT,
                occurred_at=occurred_at,
            )
        )
        self.record_event(
            UserSessionEnded(
                user_id=current_user.user_id,
                username=username,
                occurred_at=occurred_at,
            )
        )

        logger.info("Logged out user_id=%d.", current_user.user_id)
