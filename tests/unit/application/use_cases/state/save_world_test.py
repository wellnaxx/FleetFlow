import unittest
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.use_cases.state.save_world import SaveWorldStateUseCase


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

        use_case = SaveWorldStateUseCase(gateway, persistence)

        result = use_case.execute("state.json")

        gateway.build_snapshot.assert_called_once_with()
        persistence.write.assert_called_once_with("state.json", snapshot)
        self.assertEqual(result, "/abs/state.json")
