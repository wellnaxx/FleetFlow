"""Use case for browsing audit records under actor-scoped authorization."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from src.application.events.auth_events import AuthorizationDenied
from src.application.models.audit_log_query import AuditLogQuery
from src.application.models.audit_record import AuditRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin
from src.application.use_cases.pagination import PageResult, execute_page_query
from src.domain.enums.auth import Permission
from src.ports.output.audit_repository import AuditRepositoryPort


class ViewAuditLogsUseCase(AuthorizedUseCase[PageResult[AuditRecord]], ApplicationEventRecorderMixin):
    """Return audit records visible to the current principal.

    Managers with ``AUDIT_VIEW`` may query the full audit log with caller
    supplied filters. Other authenticated users may only view records produced
    by their own actor id. Attempts to query another actor are rejected and
    recorded as authorization-denied application events.
    """

    def __init__(
        self,
        audit_log_repository: AuditRepositoryPort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the audit-log reader.

        Args:
            audit_log_repository: Repository used to query persisted audit records.
            authz: Current authorization state for the workflow.
            clock: Clock used when recording authorization-denied events.
        """
        super().__init__(authz)
        self._audit_log_repository = audit_log_repository
        self._clock = clock

        self._pending_events = []

    def execute(self, query: AuditLogQuery) -> PageResult[AuditRecord]:
        """Execute an authorized audit-log query.

        Args:
            query: Pagination and filter options requested by the caller.

        Returns:
            Page result containing audit records allowed for the current principal.

        Raises:
            PermissionError: If the caller is unauthenticated or attempts to
                view audit records for another actor.
            ValidationError: Propagated from pagination validation when page
                arguments are invalid.
        """
        user = self.authz.current_user

        if user is None:
            self._record_authorization_denied(
                user_id=None,
                username=None,
                permissions=(Permission.AUDIT_VIEW,),
            )
            raise PermissionError("Unauthenticated")

        if self.authz.has(Permission.AUDIT_VIEW):
            return self._execute_query(query)

        if query.filters.actor_user_id is not None and query.filters.actor_user_id != user.user_id:
            self._record_authorization_denied(
                user_id=user.user_id,
                username=user.username,
                permissions=(Permission.AUDIT_VIEW,),
            )
            raise PermissionError("Cannot view audit logs for other users")

        if query.filters.actor_username is not None and query.filters.actor_username != user.username:
            self._record_authorization_denied(
                user_id=user.user_id,
                username=user.username,
                permissions=(Permission.AUDIT_VIEW,),
            )
            raise PermissionError("Cannot view audit logs for other users")

        effective_query = replace(
            query,
            filters=replace(query.filters, actor_user_id=user.user_id),
        )
        return self._execute_query(effective_query)

    def _execute_query(self, query: AuditLogQuery) -> PageResult[AuditRecord]:
        """Run a repository-backed page query using the supplied filters.

        Args:
            query: Validated audit-log query to execute.

        Returns:
            Page result returned by the shared pagination helper.

        Raises:
            ValidationError: If pagination arguments are invalid.
        """
        return execute_page_query(
            query=query.page,
            list_all=lambda: self._audit_log_repository.list_all(query.filters),
            list_page=lambda limit, offset: self._audit_log_repository.list_page(
                query.filters,
                limit,
                offset,
            ),
            list_page_with_total=lambda limit, offset: self._audit_log_repository.list_page_with_total(
                query.filters,
                limit,
                offset,
            ),
        )

    def _record_authorization_denied(
        self,
        user_id: int | None,
        username: str | None,
        permissions: tuple[Permission, ...],
    ) -> None:
        """Record an authorization denial for later event publication.

        Args:
            user_id: Authenticated actor id, or ``None`` when unauthenticated.
            username: Authenticated actor username, or ``None`` when unknown.
            permissions: Permissions required by the denied operation.
        """
        self._record_event(
            AuthorizationDenied(
                user_id=user_id,
                username=username,
                required_permissions=permissions,
                occurred_at=self._clock(),
            )
        )
