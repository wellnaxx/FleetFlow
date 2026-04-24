import unittest
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.use_cases.state.load_world import LoadWorldStateUseCase


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

        use_case = LoadWorldStateUseCase(gateway, persistence)

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
        gateway.apply_snapshot.side_effect = ValueError("bad snapshot")

        use_case = LoadWorldStateUseCase(gateway, persistence)

        with self.assertRaises(ValueError):
            use_case.execute("state.json")
