import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.engine import Engine


class EngineTests(unittest.TestCase):
    def make_engine(self) -> tuple[Engine, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
        factory = MagicMock()
        auth = MagicMock()
        authz = MagicMock()
        save_world = MagicMock()
        advance = MagicMock()
        engine = Engine(
            factory=factory,
            auth=auth,
            authz=authz,
            save_world_state=save_world,
            autosave_path="state.json",
            advance_world_state=advance,
        )
        return engine, factory, auth, authz, save_world, advance

    def test_rebind_app_updates_authz_current_user(self) -> None:
        engine, _factory, auth, authz, _save_world, _advance = self.make_engine()
        auth.current_user = object()

        engine._rebind_app()

        self.assertIs(authz.current_user, auth.current_user)

    def test_exec_line_runs_heartbeat_before_command_and_autosaves_mutating_commands(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()
        cmd = MagicMock()
        cmd.execute.return_value = "ok"
        cmd.mutates_state = True
        cmd.mutates_session = False
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("save state.json")

        advance.execute.assert_called_once_with()
        factory.create.assert_called_once_with("save state.json")
        cmd.execute.assert_called_once_with()
        save_world.execute.assert_called_once_with("state.json")
        mock_print.assert_called_with("ok")

    def test_exec_line_does_not_autosave_non_mutating_commands(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()
        cmd = MagicMock()
        cmd.execute.return_value = ""
        cmd.mutates_state = False
        cmd.mutates_session = False
        factory.create.return_value = cmd

        engine._exec_line("viewallroutes")

        advance.execute.assert_called_once_with()
        save_world.execute.assert_not_called()
