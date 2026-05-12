from collections.abc import Callable

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import (
    HydratedWorldGraph,
    load_world_graph,
)
from src.adapters.driven.persistence.database.snapshot_counters import load_snapshot_counters
from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldStateSnapshot
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder


class PostgresWorldStateGateway:
    """Bridge world-state snapshot use cases to the PostgreSQL database."""

    def __init__(
        self,
        snapshot_builder: WorldStateSnapshotBuilder,
        graph_loader: Callable[[], HydratedWorldGraph] = load_world_graph,
        counter_loader: Callable[[], CountersSnapshot] = load_snapshot_counters,
    ) -> None:
        """Initialize the gateway with snapshot export dependencies.

        Args:
            snapshot_builder: Builder used to construct snapshots.
            graph_loader: Callable to load the world graph (defaults to load_world_graph).
            counter_loader: Callable to load snapshot counters.
        """
        self._snapshot_builder = snapshot_builder
        self._graph_loader = graph_loader
        self._counter_loader = counter_loader

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a snapshot from the current database state.

        Returns:
            Current world-state snapshot.
        """
        graph = self._graph_loader()
        counters = self._counter_loader()
        return self._snapshot_builder.build_world_state_snapshot(
            customers=graph.customers.values(),
            packages=graph.packages.values(),
            routes=graph.routes.values(),
            trucks=graph.trucks.values(),
            counters=counters,
            schema_version=2,
        )

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Reject snapshot import because Postgres import is not implemented.

        Args:
            snapshot: Snapshot that cannot currently be applied.

        Raises:
            NotImplementedError: Always raised until Postgres import exists.
        """
        raise NotImplementedError("Postgres snapshot import is not implemented yet.")
