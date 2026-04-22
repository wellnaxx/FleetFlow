import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.commands.load_state import LoadState


class LoadStateTests(unittest.TestCase):
    def make_cmd(self, params: list[str] | None = None, *, authorized: bool = True) -> LoadState:
        cmd = LoadState.__new__(LoadState)
        cmd._params = tuple(params or [])  # type: ignore[reportAttributeAccessIssue]
        cmd._use_case = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz = MagicMock()  # type: ignore[reportAttributeAccessIssue]
        cmd._authz.has.return_value = authorized  # type: ignore[reportAttributeAccessIssue]
        return cmd

    def test_mutates_state_true(self) -> None:
        self.assertTrue(LoadState.mutates_state)

    def test_autosaves_state_false(self) -> None:
        self.assertFalse(LoadState.autosaves_state)

    def test_execute_without_permission_raises(self) -> None:
        cmd = self.make_cmd(["state.json"], authorized=False)

        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()

        self.assertIn("APP_LOAD_STATE", str(ctx.exception))
        cmd._use_case.execute.assert_not_called()  # type: ignore[reportUnknownMemberType]

    @patch("src.adapters.driving.cli.commands.load_state.validate_params_count")
    def test_execute_with_explicit_path_returns_formatted_message(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd(["/data/snapshots/state-2025-09-01.json"])
        cmd._use_case.execute.return_value = "/abs/state-2025-09-01.json"  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("/data/snapshots/state-2025-09-01.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Loaded state from /abs/state-2025-09-01.json")

    @patch("src.adapters.driving.cli.commands.load_state.validate_params_count")
    def test_execute_uses_default_filename_when_no_params(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd([])
        cmd._use_case.execute.return_value = "/abs/state.json"  # type: ignore[reportAttributeAccessIssue]

        result = cmd.execute()

        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("state.json")  # type: ignore[reportUnknownMemberType]
        self.assertEqual(result, "Loaded state from /abs/state.json")

    @patch("src.adapters.driving.cli.commands.load_state.validate_params_count")
    def test_execute_propagates_errors_from_use_case(self, mock_validate: MagicMock) -> None:
        cmd = self.make_cmd(["missing.json"])
        cmd._use_case.execute.side_effect = ValueError("not found")  # type: ignore[reportAttributeAccessIssue]

        with self.assertRaises(ValueError) as ctx:
            cmd.execute()

        self.assertIn("not found", str(ctx.exception))
        mock_validate.assert_called_once_with(cmd.params, 0, 1)
        cmd._use_case.execute.assert_called_once_with("missing.json")  # type: ignore[reportUnknownMemberType]


