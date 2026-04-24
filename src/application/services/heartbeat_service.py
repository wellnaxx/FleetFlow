from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.ports.output.route_repository import RouteRepositoryPort


class HeartbeatService:
    def __init__(
        self,
        routes: RouteRepositoryPort,
        reconciler: WorldStateReconciliationService,
    ) -> None:
        self._routes = routes
        self._reconciler = reconciler

    def advance(self, now: datetime | None = None) -> HeartbeatSummary:
        return self._reconciler.reconcile_routes(routes=self._routes.list_all(), now=now, update_trucks=True)
