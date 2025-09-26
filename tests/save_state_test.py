import unittest
from unittest.mock import MagicMock

from src.commands.save_state import SaveState


class SaveState_Should(unittest.TestCase):
    def make_cmd(self, params=None):
        cmd = SaveState.__new__(SaveState)
        cmd._params = params or []
        cmd._app_data = MagicMock()
        return cmd

    def test_no_mutates_state_flag(self):
        self.assertFalse(getattr(SaveState, "mutates_state", False))

    def test_execute_with_explicit_path_calls_save_and_returns_value(self):
        cmd = self.make_cmd(["/tmp/state-01.json"])
        cmd._app_data.save.return_value = "OK"
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("/tmp/state-01.json")
        self.assertEqual(result, "OK")

    def test_execute_uses_default_filename_when_no_params(self):
        cmd = self.make_cmd([])
        cmd._app_data.save.return_value = "saved default"
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("state.json")
        self.assertEqual(result, "saved default")

    def test_execute_ignores_extra_params_and_uses_first_only(self):
        cmd = self.make_cmd(["first.json", "second.json"])
        cmd._app_data.save.return_value = "saved first"
        result = cmd.execute()
        cmd._app_data.save.assert_called_once_with("first.json")
        self.assertEqual(result, "saved first")

    def test_execute_propagates_errors_from_app_data(self):
        cmd = self.make_cmd(["bad/dir/state.json"])
        cmd._app_data.save.side_effect = PermissionError("cannot write")
        with self.assertRaises(PermissionError) as ctx:
            cmd.execute()
        self.assertIn("cannot write", str(ctx.exception))
        cmd._app_data.save.assert_called_once_with("bad/dir/state.json")


