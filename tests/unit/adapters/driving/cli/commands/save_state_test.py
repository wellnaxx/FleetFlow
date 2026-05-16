import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.save_state import SaveState


class SaveStateShould(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None) -> SaveState:
        cmd = SaveState.__new__(SaveState)
        cmd._params = tuple(params or [])  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_no_mutates_state_flag(self) -> None:
        self.assertFalse(getattr(SaveState, "mutates_state", False))

    def test_execute_propagates_permission_errors_from_use_case(self) -> None:
        cmd = self.make_cmd(["state.json"])
        cmd._use_case.execute.side_effect = PermissionError("Missing permission: APP_SAVE_STATE")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("APP_SAVE_STATE", str(ctx.exception))
        cmd._use_case.execute.assert_called_once_with("state.json")  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.save_state.validate_params_count")
    def test_execute_with_explicit_path_returns_formatted_message(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd(["/tmp/state-01.json"])
        cmd._use_case.execute.return_value = "/abs/state-01.json"  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("/tmp/state-01.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Saved state to /abs/state-01.json")

    @patch("src.adapters.driving.cli.commands.save_state.validate_params_count")
    def test_execute_uses_default_filename_when_no_params(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd([])
        cmd._use_case.execute.return_value = "/abs/state.json"  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("state.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Saved state to /abs/state.json")

    @patch("src.adapters.driving.cli.commands.save_state.validate_params_count")
    def test_execute_propagates_errors_from_use_case(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd(["bad/dir/state.json"])
        cmd._use_case.execute.side_effect = ValueError("cannot write")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("cannot write", str(ctx.exception))
        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("bad/dir/state.json")  # type: ignore[reportUnknownMemberType]
