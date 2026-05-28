import unittest
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
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
        gateway.apply_snapshot.side_effect = WorldStateCorruptionError("bad snapshot")

        use_case = LoadWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(WorldStateCorruptionError):
            use_case.execute("state.json")

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
