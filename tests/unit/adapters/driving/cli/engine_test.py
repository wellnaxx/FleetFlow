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

        engine._rebind_app() # pyright: ignore[reportPrivateUsage]

        self.assertIs(authz.current_user, auth.current_user)

    def test_exec_line_runs_heartbeat_before_command_and_autosaves_mutating_commands(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()
        cmd = MagicMock()
        cmd.execute.return_value = "ok"
        cmd.mutates_state = True
        cmd.mutates_session = False
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("save state.json") # pyright: ignore[reportPrivateUsage]

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

        engine._exec_line("viewallroutes") # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        save_world.execute.assert_not_called()

    def test_menu_state_quotes_save_paths_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["1", "my state file.json", "0"]),
        ):
            engine._menu_state() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("save 'my state file.json'")

    def test_menu_state_quotes_load_paths_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["2", "snapshots/world state.json", "0"]),
        ):
            engine._menu_state() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("load 'snapshots/world state.json'")

    def test_menu_state_supports_command_mode_shortcut(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_command_mode") as mock_command_mode,
            patch("builtins.input", side_effect=["cmd", "0"]),
        ):
            engine._menu_state() # pyright: ignore[reportPrivateUsage]

        mock_command_mode.assert_called_once_with()

    def test_menu_packages_quotes_customer_name_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch(
                "builtins.input",
                side_effect=["1", "SYD", "MEL", "10.5", "Mary Jane", "mary@example.com", "0412345678", "0"],
            ),
        ):
            engine._menu_packages() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with(
            "createpackage SYD MEL 10.5 'Mary Jane' mary@example.com 0412345678"
        )

    def test_menu_packages_quotes_remove_and_view_ids(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["2", "pkg 42", "5", "pkg 99", "0"]),
        ):
            engine._menu_packages() # pyright: ignore[reportPrivateUsage]

        self.assertEqual(
            [call.args[0] for call in mock_exec_line.call_args_list],
            ["removepackage 'pkg 42'", "viewpackage 'pkg 99'"],
        )

    def test_menu_packages_quotes_route_lookup_id(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["4", "pkg 77", "0"]),
        ):
            engine._menu_packages() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("findsuitableroutesforpackage 'pkg 77'")

    def test_menu_packages_splits_assign_package_ids(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["3", "route-1", "pkg1 pkg2", "0"]),
        ):
            engine._menu_packages() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("assignpackagestoroute route-1 pkg1 pkg2")

    def test_menu_routes_quotes_departure_timestamp(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["1", "SYD MEL", "2025-10-12 06:00", "0"]),
        ):
            engine._menu_routes() # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("createroute SYD MEL '2025-10-12 06:00'")

    def test_menu_routes_quotes_lookup_remove_assign_and_search_ids(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch(
                "builtins.input",
                side_effect=[
                    "2",
                    "route 1",
                    "3",
                    "route 2",
                    "5",
                    "truck 4",
                    "route 5",
                    "6",
                    "route 6",
                    "0",
                ],
            ),
        ):
            engine._menu_routes() # pyright: ignore[reportPrivateUsage]

        self.assertEqual(
            [call.args[0] for call in mock_exec_line.call_args_list],
            [
                "viewroute 'route 1'",
                "removeroute 'route 2'",
                "assigntrucktoroute 'truck 4' 'route 5'",
                "findsuitabletrucksforroute 'route 6'",
            ],
        )

    def test_exec_line_warns_on_unexpected_exception(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()
        cmd = MagicMock()
        cmd.execute.side_effect = RuntimeError("boom")
        cmd.mutates_state = False
        cmd.mutates_session = False
        factory.create.return_value = cmd

        with (
            patch("builtins.print") as mock_print,
            patch("src.adapters.driving.cli.engine.logger") as mock_logger,
        ):
            engine._exec_line("viewallroutes") # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        mock_logger.exception.assert_called_once_with(
            "Unexpected CLI error while executing %r",
            "viewallroutes",
        )
        mock_print.assert_called_with("Unexpected error: boom")
