import unittest
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import WorldStatePersistenceError
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from tests.unit.application.use_cases.authz_helpers import manager_authz


class SaveWorldStateUseCaseTests(unittest.TestCase):
    def test_execute_builds_snapshot_and_writes_it(self) -> None:
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
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.return_value = "/abs/state.json"

        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        result = use_case.execute("state.json")

        gateway.build_snapshot.assert_called_once_with()
        persistence.write.assert_called_once_with("state.json", snapshot)
        self.assertEqual(result, "/abs/state.json")

    def test_execute_rejects_blank_path_before_building_snapshot(self) -> None:
        gateway = MagicMock()
        persistence = MagicMock()
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("   ")

        self.assertIn("World state snapshot path is required.", str(ctx.exception))
        gateway.build_snapshot.assert_not_called()
        persistence.write.assert_not_called()

    def test_execute_wraps_invalid_persistence_path(self) -> None:
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
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.side_effect = ValueError("Invalid snapshot path.")
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(ValidationError) as ctx:
            use_case.execute("bad")

        self.assertIn("Invalid snapshot path.", str(ctx.exception))

    def test_execute_wraps_write_os_error(self) -> None:
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
        gateway.build_snapshot.return_value = snapshot
        persistence = MagicMock()
        persistence.write.side_effect = OSError("denied")
        use_case = SaveWorldStateUseCase(gateway, persistence, manager_authz())

        with self.assertRaises(WorldStatePersistenceError) as ctx:
            use_case.execute("state.json")

        self.assertIn("Could not write world state snapshot.", str(ctx.exception))
