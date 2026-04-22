import unittest
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.engine import Engine


class EngineTests(unittest.TestCase):
    def make_engine(self) -> tuple[Engine, MagicMock, MagicMock, MagicMock, MagicMock]:
        factory = MagicMock()
        app = MagicMock()
        auth = MagicMock()
        authz = MagicMock()
        autosave = MagicMock()
        engine = Engine(factory=factory, app=app, auth=auth, authz=authz, autosave_world_state=autosave)
        return engine, factory, app, auth, authz, autosave

    def test_rebind_app_updates_authz_current_user(self) -> None:
        engine, _factory, _app, auth, authz, _autosave = self.make_engine()
        auth.current_user = object()

        engine._rebind_app()

        self.assertIs(authz.current_user, auth.current_user)

    def test_exec_line_runs_heartbeat_before_command_and_autosaves_mutating_commands(self) -> None:
        engine, factory, app, _auth, _authz, autosave = self.make_engine()
        cmd = MagicMock()
        cmd.execute.return_value = "ok"
        cmd.mutates_state = True
        cmd.mutates_session = False
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("save state.json")

        app.heartbeat.assert_called_once_with()
        factory.create.assert_called_once_with("save state.json")
        cmd.execute.assert_called_once_with()
        autosave.execute.assert_called_once_with()
        mock_print.assert_called_with("ok")

    def test_exec_line_does_not_autosave_non_mutating_commands(self) -> None:
        engine, factory, app, _auth, _authz, autosave = self.make_engine()
        cmd = MagicMock()
        cmd.execute.return_value = ""
        cmd.mutates_state = False
        cmd.mutates_session = False
        factory.create.return_value = cmd

        engine._exec_line("viewallroutes")

        app.heartbeat.assert_called_once_with()
        autosave.execute.assert_not_called()
