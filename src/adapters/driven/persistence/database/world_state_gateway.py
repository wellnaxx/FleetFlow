import logging
from collections.abc import Callable

from src.adapters.driven.persistence.database.graph_loaders.world_graph_loader import (
    HydratedWorldGraph,
    load_world_graph,
)
from src.adapters.driven.persistence.database.snapshot_counters import load_snapshot_counters
from src.adapters.driven.persistence.database.world_state_importer import PostgresWorldStateImporter
from src.application.dto.world_state_snapshot_dto import CountersSnapshot, WorldStateSnapshot
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.application.services.world_state_schema import SCHEMA_VERSION, SUPPORTED_SCHEMA_VERSIONS
from src.application.services.world_state_snapshot_builder import WorldStateSnapshotBuilder
from src.application.services.world_state_snapshot_preparer import WorldStateSnapshotPreparer

logger = logging.getLogger(__name__)


class PostgresWorldStateGateway:
    """Bridge world-state snapshot use cases to the PostgreSQL database."""

    def __init__(
        self,
        snapshot_builder: WorldStateSnapshotBuilder,
        snapshot_preparer: WorldStateSnapshotPreparer,
        importer: PostgresWorldStateImporter,
        graph_loader: Callable[[], HydratedWorldGraph] = load_world_graph,
        counter_loader: Callable[[], CountersSnapshot] = load_snapshot_counters,
    ) -> None:
        """Initialize the gateway with snapshot export dependencies.

        Args:
            snapshot_builder: Builder used to construct snapshots.
            snapshot_preparer: Preparer used to validate and prepare snapshots for import.
            importer: Component responsible for importing prepared snapshots into the database.
            graph_loader: Callable to load the world graph (defaults to load_world_graph).
            counter_loader: Callable to load snapshot counters.
        """
        self._snapshot_builder = snapshot_builder
        self._snapshot_preparer = snapshot_preparer
        self._graph_loader = graph_loader
        self._counter_loader = counter_loader
        self._importer = importer

    def build_snapshot(self) -> WorldStateSnapshot:
        """Build a snapshot from the current database state.

        Returns:
            Current world-state snapshot.
        """
        logger.info("Building PostgreSQL world-state snapshot.")
        graph = self._graph_loader()
        counters = self._counter_loader()
        snapshot = self._snapshot_builder.build_world_state_snapshot(
            customers=graph.customers.values(),
            packages=graph.packages.values(),
            routes=graph.routes.values(),
            trucks=graph.trucks.values(),
            counters=counters,
            schema_version=SCHEMA_VERSION,
        )
        logger.info(
            "Built PostgreSQL world-state snapshot with %d customers, %d packages, %d routes, and %d trucks.",
            len(graph.customers),
            len(graph.packages),
            len(graph.routes),
            len(graph.trucks),
        )
        return snapshot

    def apply_snapshot(self, snapshot: WorldStateSnapshot) -> None:
        """Apply a snapshot to the database, replacing existing state.

        Args:
            snapshot: The world-state snapshot to apply.

        Raises:
            WorldStateCorruptionError: If the snapshot is invalid or cannot be applied.
            DatabaseError: If there is an error during database operations.
        """
        logger.info("Applying world-state snapshot to PostgreSQL backend.")
        try:
            reconciled_world = self._snapshot_preparer.prepare(snapshot, SUPPORTED_SCHEMA_VERSIONS)
        except (KeyError, TypeError, ValueError) as exc:
            raise WorldStateCorruptionError(f"Invalid world state snapshot: {exc}") from exc

        self._importer.import_world(reconciled_world)
        logger.info("PostgreSQL world-state snapshot import completed.")
