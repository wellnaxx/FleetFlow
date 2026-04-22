import unittest
from unittest.mock import MagicMock

from src.application.dto.world_state_snapshot_dto import (
    CountersSnapshot,
    WorldSnapshotData,
    WorldStateSnapshot,
)
from src.application.use_cases.state.load_world import LoadWorldStateUseCase


class LoadWorldStateUseCaseTests(unittest.TestCase):
    def test_execute_reads_snapshot_applies_it_and_advances_world_state(self) -> None:
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
        advance_world_state = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)

        use_case = LoadWorldStateUseCase(gateway, persistence, advance_world_state)

        result = use_case.execute("state.json")

        persistence.read.assert_called_once_with("state.json")
        gateway.apply_snapshot.assert_called_once_with(snapshot)
        advance_world_state.execute.assert_called_once_with()
        self.assertEqual(result, "/abs/state.json")

    def test_execute_does_not_advance_when_apply_fails(self) -> None:
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
        advance_world_state = MagicMock()
        persistence.read.return_value = ("/abs/state.json", snapshot)
        gateway.apply_snapshot.side_effect = ValueError("bad snapshot")

        use_case = LoadWorldStateUseCase(gateway, persistence, advance_world_state)

        with self.assertRaises(ValueError):
            use_case.execute("state.json")

        advance_world_state.execute.assert_not_called()
