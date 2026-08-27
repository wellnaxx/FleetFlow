import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.commands.state.save_world import SaveWorldCommand
from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import WorldStateExported, WorldStateExportFailed
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStatePersistenceError
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from tests.unit.application.use_cases.authz_helpers import manager_authz


class SaveWorldStateUseCaseTests(unittest.TestCase):
    def _snapshot(self) -> WorldStateSnapshot:
        return WorldStateSnapshot(
            schema_version=2,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
            ),
        )

    def test_execute_builds_snapshot_and_writes_it(self) -> None:
        snapshot = self._snapshot()
        gateway = MagicMock()
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.return_value = "/abs/state.json"

        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        result = use_case.execute(SaveWorldCommand(path="state.json"))

        gateway.build_snapshot.assert_called_once_with()
        persistence.write.assert_called_once_with("state.json", snapshot)
        self.assertEqual(result, "/abs/state.json")

    def test_execute_records_exported_event(self) -> None:
        snapshot = self._snapshot()
        gateway = MagicMock()
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.return_value = "/abs/state.json"
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = SaveWorldStateUseCase(
            gateway,
            persistence,
            manager_authz(),
            clock=lambda: occurred_at,
        )

        use_case.execute(SaveWorldCommand(path="state.json"))

        event = use_case.pending_events[0]
        self.assertIsInstance(event, WorldStateExported)
        assert isinstance(event, WorldStateExported)
        self.assertEqual(event.snapshot_path, "/abs/state.json")
        self.assertEqual(event.schema_version, 2)
        self.assertEqual(
            event.entity_counts,
            WorldStateEntityCounts(customers=0, packages=0, routes=0, trucks=0),
        )
        self.assertEqual(event.occurred_at, occurred_at)

    def test_execute_strips_path_before_writing_snapshot(self) -> None:
        snapshot = self._snapshot()
        gateway = MagicMock()
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.return_value = "/abs/state.json"
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        result = use_case.execute(SaveWorldCommand(path="  state.json  "))

        persistence.write.assert_called_once_with("state.json", snapshot)
        self.assertEqual(result, "/abs/state.json")

    def test_execute_rejects_blank_path_before_building_snapshot(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute(SaveWorldCommand(path="   "))

        self.assertIn("World state snapshot path is required.", str(ctx.exception))
        gateway.build_snapshot.assert_not_called()
        persistence.write.assert_not_called()
        self._assert_export_failed(
            use_case,
            snapshot_path="   ",
            schema_version=None,
            reason=WorldStateFailureReason.INVALID_PATH,
            occurred_at=occurred_at,
        )

    def test_execute_wraps_invalid_persistence_path(self) -> None:
        snapshot = self._snapshot()
        gateway = MagicMock()
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.side_effect = ValueError("Invalid snapshot path.")
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute(SaveWorldCommand(path="bad"))

        self.assertIn("Invalid snapshot path.", str(ctx.exception))
        self._assert_export_failed(
            use_case,
            snapshot_path="bad",
            schema_version=2,
            reason=WorldStateFailureReason.INVALID_PATH,
            occurred_at=occurred_at,
        )

    def test_execute_wraps_write_os_error(self) -> None:
        snapshot = self._snapshot()
        gateway = MagicMock()
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.side_effect = OSError("denied")
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz(), clock=lambda: occurred_at)

        with self.assertRaises(WorldStatePersistenceError) as ctx:
            use_case.execute(SaveWorldCommand(path="state.json"))

        self.assertIn("Could not write world state snapshot.", str(ctx.exception))
        self._assert_export_failed(
            use_case,
            snapshot_path="state.json",
            schema_version=2,
            reason=WorldStateFailureReason.PERSISTENCE_FAILURE,
            occurred_at=occurred_at,
        )

    def _assert_export_failed(
        self,
        use_case: SaveWorldStateUseCase,
        *,
        snapshot_path: str,
        schema_version: int | None,
        reason: WorldStateFailureReason,
        occurred_at: datetime,
    ) -> None:
        self.assertEqual(len(use_case.pending_events), 1)
        event = use_case.pending_events[0]
        self.assertIsInstance(event, WorldStateExportFailed)
        assert isinstance(event, WorldStateExportFailed)
        self.assertEqual(event.snapshot_path, snapshot_path)
        self.assertEqual(event.schema_version, schema_version)
        self.assertIs(event.reason, reason)
        self.assertEqual(event.occurred_at, occurred_at)
