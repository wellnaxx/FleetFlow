import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateImportFailed,
)
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStateCorruptionError, WorldStatePersistenceError
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class LoadWorldStateUseCaseTests(unittest.TestCase):
    def test_execute_reads_snapshot_and_applies_it(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
            ),
        )
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)

        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        result = use_case.execute("state.json")

        persistence.read.assert_called_once_with("state.json")
        gateway.apply_snapshot.assert_called_once_with(snapshot)
        self.assertEqual(result, "/abs/state.json")

    def test_execute_strips_path_before_reading_snapshot(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
            ),
        )
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)
        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        result = use_case.execute("  state.json  ")

        persistence.read.assert_called_once_with("state.json")
        gateway.apply_snapshot.assert_called_once_with(snapshot)
        self.assertEqual(result, "/abs/state.json")

    def test_execute_raises_when_apply_fails(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=1,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
            ),
        )
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)
        gateway.apply_snapshot.side_effect = WorldStateCorruptionError(
            "bad snapshot",
            reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
        )

        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(WorldStateCorruptionError):
            use_case.execute("state.json")

    def test_execute_records_corruption_events_when_read_snapshot_is_corrupt(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.side_effect = WorldStateCorruptionError(
            "bad snapshot",
            reason=WorldStateCorruptionReason.MALFORMED_JSON,
        )
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LoadWorldStateUseCase(
            gateway,
            persistence,
            manager_authz(),
            clock=lambda: occurred_at,
        )

        with self.assertRaises(WorldStateCorruptionError):
            use_case.execute("state.json")

        import_failed, corruption_detected = use_case.pending_events
        self.assertIsInstance(import_failed, WorldStateImportFailed)
        self.assertIsInstance(corruption_detected, WorldStateCorruptionDetected)
        assert isinstance(import_failed, WorldStateImportFailed)
        assert isinstance(corruption_detected, WorldStateCorruptionDetected)
        self.assertEqual(import_failed.snapshot_path, "state.json")
        self.assertIsNone(import_failed.schema_version)
        self.assertIs(import_failed.reason, WorldStateFailureReason.CORRUPT_SNAPSHOT)
        self.assertEqual(import_failed.occurred_at, occurred_at)
        self.assertEqual(corruption_detected.snapshot_path, "state.json")
        self.assertIs(corruption_detected.reason, WorldStateCorruptionReason.MALFORMED_JSON)
        self.assertEqual(corruption_detected.occurred_at, occurred_at)
        gateway.apply_snapshot.assert_not_called()

    def test_execute_records_corruption_events_when_apply_snapshot_is_corrupt(self) -> None:
        snapshot = WorldStateSnapshot(
            schema_version=2,
            world=WorldSnapshotData(
                counters=CountersSnapshot(1, 1, 1),
                customers=(),
                packages=(),
                routes=(),
            ),
        )
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)
        gateway.apply_snapshot.side_effect = WorldStateCorruptionError(
            "bad snapshot",
            reason=WorldStateCorruptionReason.INVALID_REFERENCES,
        )
        occurred_at = datetime(2025, 1, 1, 12, 0)
        use_case = LoadWorldStateUseCase(
            gateway,
            persistence,
            manager_authz(),
            clock=lambda: occurred_at,
        )

        with self.assertRaises(WorldStateCorruptionError):
            use_case.execute("state.json")

        import_failed, corruption_detected = use_case.pending_events
        self.assertIsInstance(import_failed, WorldStateImportFailed)
        self.assertIsInstance(corruption_detected, WorldStateCorruptionDetected)
        assert isinstance(import_failed, WorldStateImportFailed)
        assert isinstance(corruption_detected, WorldStateCorruptionDetected)
        self.assertEqual(import_failed.snapshot_path, "/abs/state.json")
        self.assertEqual(import_failed.schema_version, 2)
        self.assertIs(import_failed.reason, WorldStateFailureReason.CORRUPT_SNAPSHOT)
        self.assertEqual(import_failed.occurred_at, occurred_at)
        self.assertEqual(corruption_detected.snapshot_path, "/abs/state.json")
        self.assertIs(corruption_detected.reason, WorldStateCorruptionReason.INVALID_REFERENCES)
        self.assertEqual(corruption_detected.occurred_at, occurred_at)

    def test_execute_rejects_blank_path_before_reading_snapshot(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("   ")

        self.assertIn("World state snapshot path is required.", str(ctx.exception))
        persistence.read.assert_not_called()
        gateway.apply_snapshot.assert_not_called()

    def test_execute_wraps_invalid_persistence_path(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.side_effect = ValueError("Invalid snapshot path.")
        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("bad")

        self.assertIn("Invalid snapshot path.", str(ctx.exception))
        gateway.apply_snapshot.assert_not_called()

    def test_execute_wraps_read_os_error(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        persistence.read.side_effect = OSError("denied")
        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(WorldStatePersistenceError) as ctx:
            use_case.execute("state.json")

        self.assertIn("Could not read world state snapshot.", str(ctx.exception))
        gateway.apply_snapshot.assert_not_called()
