"""Application service for advancing runtime world state."""

from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.ports.output.route_repository import RouteRepositoryPort


class HeartbeatService:
    """Runs route, package, and truck reconciliation for all routes."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        reconciler: WorldStateReconciliationService,
    ) -> None:
        """Initialize heartbeat dependencies.

        Args:
            routes: Repository providing routes to reconcile.
            reconciler: Service that applies route/package/truck state updates.
        """
        self._routes = routes
        self._reconciler = reconciler

    def advance(self, now: datetime | None = None) -> HeartbeatSummary:
        """Advance world state to the given time or the current time.

        Args:
            now: Optional reconciliation time. When omitted, the reconciler uses
                the current wall-clock time.

        Returns:
            Summary of route, package, and truck changes.
        """
        return self._reconciler.reconcile_routes(routes=self._routes.list_all(), now=now, update_trucks=True)
