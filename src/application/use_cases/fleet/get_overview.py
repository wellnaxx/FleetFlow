"""Use case for retrieving the current cross-aggregate fleet overview."""

from collections.abc import Callable
from datetime import datetime

from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.exceptions.application_errors import ValidationError
from src.application.results.fleet_overview import FleetOverview
from src.application.services.authorization_service import AuthorizationService, requires
from src.application.use_cases.base.authorized_use_case import AuthorizedUseCase
from src.domain.enums.auth import Permission
from src.ports.output.fleet_overview_query import FleetOverviewQueryPort


class GetFleetOverviewUseCase(AuthorizedUseCase[FleetOverview]):
    """Return an authorized point-in-time fleet operations overview.

    The use case owns the generation timestamp so every count, deadline, and
    active-route position is evaluated against one clock value. Persistence
    adapters remain responsible for building a coherent snapshot for that
    timestamp.
    """

    def __init__(
        self,
        overview_query: FleetOverviewQueryPort,
        authz: AuthorizationService,
        clock: Callable[[], datetime] = datetime.now,
    ) -> None:
        """Initialize the fleet-overview workflow.

        Args:
            overview_query: Output port that builds the overview projection.
            authz: Current authorization state for the workflow.
            clock: App-local business clock used once per successful request
                and when recording authorization denials.
        """
        super().__init__(authz)
        self._overview_query = overview_query
        self._clock = clock

    @requires(
        Permission.FLEET_OVERVIEW_VIEW,
        operation=AuthorizationOperation.FLEET_OVERVIEW_VIEW,
        target_resource_type=AuditResourceType.FLEET,
        target_resource_id_resolver=None,
    )
    def execute(self, active_route_limit: int = 10) -> FleetOverview:
        """Return the fleet overview evaluated at the current business time.

        Args:
            active_route_limit: Maximum active-route projections to include,
                from 1 through 100. Defaults to 10.

        Returns:
            Point-in-time package, route, truck, and active-route summary.

        Raises:
            PermissionError: If the caller is unauthenticated or lacks fleet
                overview permission.
            ValidationError: If the limit, clock value, or persisted overview
                data violates the query contract.
            DatabaseError: If the persistence query fails.
            RuntimeError: If an active route cannot be projected from its
                persisted scheduling data.
        """
        try:
            return self._overview_query.get_overview(
                generated_at=self._clock(),
                active_route_limit=active_route_limit,
            )
        except (TypeError, ValueError) as exc:
            raise ValidationError(str(exc)) from exc
