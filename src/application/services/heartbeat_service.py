"""Application service for advancing runtime world state."""

import logging
from datetime import datetime

from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.application.services.world_state_reconciliation_service import WorldStateReconciliationService
from src.ports.output.route_repository import RouteRepositoryPort
from src.ports.output.unit_of_work import UnitOfWorkPort

logger = logging.getLogger(__name__)


class HeartbeatService:
    """Runs route, package, and truck reconciliation for all routes."""

    def __init__(
        self,
        routes: RouteRepositoryPort,
        reconciler: WorldStateReconciliationService,
        unit_of_work: UnitOfWorkPort,
    ) -> None:
        """Initialize heartbeat dependencies.

        Args:
            routes: Repository providing routes to reconcile.
            reconciler: Service that applies route/package/truck state updates.
            unit_of_work: Transaction boundary used to persist package, route, and truck
                state together after reconciliation.
        """
        self._routes = routes
        self._reconciler = reconciler
        self._unit_of_work = unit_of_work

    def advance(self, now: datetime | None = None) -> HeartbeatSummary:
        """Advance world state to the given time or the current time.

        Args:
            now: Optional reconciliation time. When omitted, the reconciler uses
                the current wall-clock time.

        Returns:
            Summary of route, package, and truck changes.
        """
        routes = self._routes.list_all()

        route_snapshots = [(route, route.snapshot_state()) for route in routes]
        package_snapshots = [
            (package, package.snapshot_state()) for route in routes for package in route.packages
        ]
        truck_snapshots = [
            (route.truck, route.truck.snapshot_state()) for route in routes if route.truck is not None
        ]

        try:
            summary = self._reconciler.reconcile_routes(
                routes=routes,
                now=now,
                update_trucks=True,
            )

            if not summary.state_changed:
                return summary

            with self._unit_of_work as uow:
                for route in summary.mutated_routes:
                    uow.routes.update_state(route)

                for package in summary.mutated_packages:
                    uow.packages.update_state(package)

                for truck in {*summary.mutated_trucks_moved, *summary.mutated_trucks_released}:
                    uow.trucks.update_state(truck)

                uow.commit()

        except Exception:
            logger.exception("Heartbeat reconciliation failed; restoring in-memory state")
            for route, snapshot in route_snapshots:
                route.restore_state(snapshot)

            for package, snapshot in package_snapshots:
                package.restore_state(snapshot)

            for truck, snapshot in truck_snapshots:
                truck.restore_state(snapshot)

            raise

        else:
            return summary
