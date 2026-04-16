import unittest
from unittest.mock import MagicMock

from adapters.driving.cli.commands.save_state import SaveState


class SaveState_Should(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> SaveState:
        cmd = SaveState.__new__(SaveState)
        cmd._params = params or []  # type: ignore[reportAttributeAccessIssue]
        cmd._app_data = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_no_mutates_state_flag(self) -> None:
        self.assertFalse(getattr(SaveState, "mutates_state", False))

    def test_execute_with_explicit_path_calls_save_and_returns_value(self) -> None:
        cmd = self.make_cmd(["/tmp/state-01.json"])
        cmd._app_data.save.return_value = "OK"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("/tmp/state-01.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "OK")

    def test_execute_uses_default_filename_when_no_params(self) -> None:
        cmd = self.make_cmd([])
        cmd._app_data.save.return_value = "saved default"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("state.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "saved default")

    def test_execute_ignores_extra_params_and_uses_first_only(self) -> None:
        cmd = self.make_cmd(["first.json", "second.json"])
        cmd._app_data.save.return_value = "saved first"  # type: ignore[reportAttributeAccessIssue]
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("first.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "saved first")

    def test_execute_propagates_errors_from_app_data(self) -> None:
        cmd = self.make_cmd(["bad/dir/state.json"])
        cmd._app_data.save.side_effect = PermissionError("cannot write")  # type: ignore[reportAttributeAccessIssue]
        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("cannot write", str(ctx.exception))
        cmd._app_data.save.assert_called_once_with("bad/dir/state.json")  # type: ignore[reportUnknownMemberType]
