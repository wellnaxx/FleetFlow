import unittest
from unittest.mock import MagicMock

from src.commands.load_state import LoadState


class LoadState_Tests(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> LoadState:
        cmd = LoadState.__new__(LoadState)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(LoadState.mutates_state)

    def test_execute_with_explicit_path_calls_load_and_returns_value(self) -> None:
        cmd = self.make_cmd(["/data/snapshots/state-2025-09-01.json"])
        cmd._app_data.load.return_value = "OK"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.load.assert_called_once_with("/data/snapshots/state-2025-09-01.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "OK")

    def test_execute_uses_default_filename_when_no_params(self) -> None:
        cmd = self.make_cmd([])
        cmd._app_data.load.return_value = "loaded default"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.load.assert_called_once_with("state.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "loaded default")

    def test_execute_ignores_extra_params_and_uses_first_only(self) -> None:
        cmd = self.make_cmd(["first.json", "second.json", "third.json"])
        cmd._app_data.load.return_value = "loaded first"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.load.assert_called_once_with("first.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "loaded first")

    def test_execute_propagates_errors_from_app_data(self) -> None:
        cmd = self.make_cmd(["missing.json"])
        cmd._app_data.load.side_effect = FileNotFoundError("not found")  # type: ignore[reportAttributeAccessIssue]
        with self.assertRaises(FileNotFoundError) as ctx:
            cmd.execute()
        self.assertIn("not found", str(ctx.exception))
        cmd._app_data.load.assert_called_once_with("missing.json")  # type: ignore[reportUnknownMemberType]
