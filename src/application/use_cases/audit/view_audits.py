"""Use case for browsing audit records under actor-scoped authorization."""

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.models.audit_log_query import AuditLogQuery
from src.application.models.audit_record import AuditRecord
from src.application.services.authorization_service import AuthorizationService, record_authorization_denied
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.application.use_cases.pagination import PageResult, execute_page_query
from src.domain.enums.auth import Permission
from src.ports.output.audit_repository import AuditRepositoryPort


class ViewAuditLogsUseCase(AuthorizedUseCase[PageResult[AuditRecord]]):
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
            record_authorization_denied(
                self,
                (Permission.AUDIT_VIEW,),
                operation=AuthorizationOperation.AUDIT_LOG_VIEW,
                target_resource_type=AuditResourceType.AUDIT_LOG,
                target_resource_id=None,
                occurred_at=self._clock(),
            )
            raise PermissionError("Unauthenticated")

        if self.authz.has(Permission.AUDIT_VIEW):
            return self._execute_query(query)

        if query.filters.actor_user_id is not None and query.filters.actor_user_id != user.user_id:
            record_authorization_denied(
                self,
                (Permission.AUDIT_VIEW,),
                operation=AuthorizationOperation.AUDIT_LOG_VIEW,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=query.filters.actor_user_id,
                occurred_at=self._clock(),
            )
            raise PermissionError("Cannot view audit logs for other users")

        if query.filters.actor_username is not None and query.filters.actor_username != user.username:
            record_authorization_denied(
                self,
                (Permission.AUDIT_VIEW,),
                operation=AuthorizationOperation.AUDIT_LOG_VIEW,
                target_resource_type=AuditResourceType.USER,
                target_resource_id=query.filters.actor_username,
                occurred_at=self._clock(),
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
