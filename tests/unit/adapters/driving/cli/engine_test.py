import unittest
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.engine import Engine
from src.application.enums.event_sources import EventSource
from src.application.eventing.current_context import get_event_context, get_optional_event_context
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.results.heartbeat_summary_result import HeartbeatSummary
from src.domain.enums.auth import Role

if TYPE_CHECKING:
    from src.application.eventing.context import EventContext


def _principal(user_id: int = 7, username: str = "fleet.manager") -> CurrentUserPrincipal:
    return CurrentUserPrincipal(
        user_id=user_id,
        username=username,
        name="Fleet Manager",
        email="manager@example.com",
        phone_number="0412345678",
        role=Role.MANAGER,
    )


class EngineTests(unittest.TestCase):
    def setUp(self) -> None:
        self._print_patcher = patch("builtins.print")
        self._print_patcher.start()

    def tearDown(self) -> None:
        self._print_patcher.stop()

    def make_engine(
        self, *, autosave_enabled: bool = True
    ) -> tuple[Engine, MagicMock, MagicMock, MagicMock, MagicMock, MagicMock]:
        factory = MagicMock()
        auth = MagicMock()
        auth.current_user = None
        authz = MagicMock()
        save_world = MagicMock()
        advance = MagicMock()
        event_collector = MagicMock()
        advance.execute.return_value = HeartbeatSummary(
            mutated_routes=(),
            mutated_packages=(),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
        )
        engine = Engine(
            factory=factory,
            auth=auth,
            authz=authz,
            save_world_state=save_world,
            autosave_path="state.json",
            advance_world_state=advance,
            autosave_enabled=autosave_enabled,
            event_collector=event_collector,
        )
        return engine, factory, auth, authz, save_world, advance

    def test_rebind_app_updates_authz_current_user(self) -> None:
        engine, _factory, auth, authz, _save_world, _advance = self.make_engine()
        auth.current_user = _principal()

        engine._rebind_app()  # pyright: ignore[reportPrivateUsage]

        self.assertIs(authz.current_user, auth.current_user)

    def test_start_dispatches_main_menu_action_and_exits(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["4", "0"]),
        ):
            engine.start()

        mock_exec_line.assert_called_once_with("viewallcustomers")
        self.assertFalse(engine._running)  # pyright: ignore[reportPrivateUsage]

    def test_start_accepts_command_mode_alias(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_command_mode") as mock_command_mode,
            patch("builtins.input", side_effect=["command", "0"]),
        ):
            engine.start()

        mock_command_mode.assert_called_once_with()

    def test_start_reports_invalid_main_menu_choice(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.print") as mock_print,
            patch("builtins.input", side_effect=["invalid", "0"]),
        ):
            engine.start()

        mock_print.assert_any_call("Invalid option. Type a number from the menu, or 'cmd' for command mode.")

    def test_submenu_input_interrupt_returns_to_main_menu(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.print") as mock_print,
            patch("builtins.input", side_effect=KeyboardInterrupt),
        ):
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

        mock_print.assert_any_call("\n(back to main menu)")

    def test_submenu_action_interrupt_keeps_submenu_open(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()
        render = MagicMock()
        action = MagicMock(side_effect=KeyboardInterrupt)

        with (
            patch("builtins.print") as mock_print,
            patch("builtins.input", side_effect=["1", "0"]),
        ):
            engine._run_submenu(  # pyright: ignore[reportPrivateUsage]
                render=render,
                actions={"1": action},
                name="Packages",
            )

        action.assert_called_once_with()
        self.assertEqual(render.call_count, 2)
        mock_print.assert_any_call("\n(cancelled Packages operation)")

    def test_exec_line_runs_heartbeat_for_normal_command(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.return_value = "ok"
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("viewroute 1")  # pyright: ignore[reportPrivateUsage]

        factory.create.assert_called_once_with("viewroute 1")
        advance.execute.assert_called_once_with()
        cmd.execute.assert_called_once_with()
        mock_print.assert_called_once_with("ok")

    def test_exec_line_binds_one_cli_context_for_heartbeat_command_and_autosave(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()
        observed_contexts: list[EventContext] = []

        def execute_command() -> str:
            observed_contexts.append(get_event_context())
            return "ok"

        def advance_world() -> HeartbeatSummary:
            observed_contexts.append(get_event_context())
            return HeartbeatSummary(
                mutated_routes=(),
                mutated_packages=(),
                mutated_trucks_moved=(),
                mutated_trucks_released=(),
            )

        def autosave(_path: str) -> None:
            observed_contexts.append(get_event_context())

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = True
        cmd.mutates_session = False
        cmd.autosaves_state = True
        cmd.execute.side_effect = execute_command
        factory.create.return_value = cmd
        advance.execute.side_effect = advance_world
        save_world.execute.side_effect = autosave

        engine._exec_line("createroute SYD MEL")  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(len(observed_contexts), 3)
        self.assertTrue(all(context is observed_contexts[0] for context in observed_contexts))
        self.assertIs(observed_contexts[0].source, EventSource.CLI)
        self.assertIsNone(observed_contexts[0].actor)
        self.assertIsNone(get_optional_event_context())

    def test_exec_line_binds_authenticated_actor_from_pre_command_session(self) -> None:
        engine, factory, auth, _authz, _save_world, _advance = self.make_engine()
        auth.current_user = _principal(user_id=7, username="fleet.manager")
        observed_contexts: list[EventContext] = []

        def execute_command() -> str:
            observed_contexts.append(get_event_context())
            return "ok"

        cmd = MagicMock()
        cmd.skips_heartbeat = True
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.side_effect = execute_command
        factory.create.return_value = cmd

        engine._exec_line("viewallroutes")  # pyright: ignore[reportPrivateUsage]

        context = observed_contexts[0]
        self.assertIs(context.source, EventSource.CLI)
        self.assertIsNotNone(context.actor)
        assert context.actor is not None
        self.assertEqual(context.actor.user_id, 7)
        self.assertEqual(context.actor.username, "fleet.manager")
        self.assertIsNone(get_optional_event_context())

    def test_exec_line_skips_heartbeat_for_opt_out_command(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = True
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.return_value = "ok"
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("whoami")  # pyright: ignore[reportPrivateUsage]

        factory.create.assert_called_once_with("whoami")
        advance.execute.assert_not_called()
        cmd.execute.assert_called_once_with()
        mock_print.assert_called_once_with("ok")

    def test_exec_line_autosaves_mutating_commands(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = True
        cmd.mutates_session = False
        cmd.autosaves_state = True
        cmd.execute.return_value = "ok"
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("save state.json")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        cmd.execute.assert_called_once_with()
        save_world.execute.assert_called_once_with("state.json")
        event_collector: MagicMock = engine._event_collector  # pyright: ignore[reportPrivateUsage, reportAssignmentType]
        event_collector.drain.assert_called_once_with((save_world,))
        mock_print.assert_called_once_with("ok")

    def test_exec_line_does_not_autosave_non_mutating_commands(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.return_value = ""
        factory.create.return_value = cmd

        engine._exec_line("viewallroutes")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        save_world.execute.assert_not_called()

    def test_exec_line_autosaves_when_heartbeat_changes_state(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.return_value = "ok"
        factory.create.return_value = cmd
        package_recorder = MagicMock()
        advance.execute.return_value = HeartbeatSummary(
            mutated_routes=(),
            mutated_packages=(package_recorder,),
            mutated_trucks_moved=(),
            mutated_trucks_released=(),
        )

        with patch("builtins.print") as mock_print:
            engine._exec_line("viewallroutes")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        save_world.execute.assert_called_once_with("state.json")
        event_collector: MagicMock = engine._event_collector  # pyright: ignore[reportPrivateUsage, reportAssignmentType]
        self.assertEqual(event_collector.drain.call_count, 2)
        event_collector.drain.assert_any_call((package_recorder, advance))
        event_collector.drain.assert_any_call((save_world,))
        mock_print.assert_called_once_with("ok")

    def test_exec_line_rebinds_after_session_mutation(self) -> None:
        engine, factory, auth, authz, _save_world, advance = self.make_engine()
        auth.current_user = _principal()

        cmd = MagicMock()
        cmd.skips_heartbeat = True
        cmd.mutates_state = False
        cmd.mutates_session = True
        cmd.autosaves_state = False
        cmd.execute.return_value = "logged in"
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("login admin")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_not_called()
        self.assertIs(authz.current_user, auth.current_user)
        mock_print.assert_called_once_with("logged in")

    def test_exec_line_warns_when_autosave_fails(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = True
        cmd.mutates_session = False
        cmd.autosaves_state = True
        cmd.execute.return_value = "ok"
        factory.create.return_value = cmd

        save_world.execute.side_effect = OSError("disk full")

        with (
            patch("builtins.print") as mock_print,
            patch("src.adapters.driving.cli.engine.logger") as mock_logger,
        ):
            engine._exec_line("createroute A B")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        event_collector: MagicMock = engine._event_collector  # pyright: ignore[reportPrivateUsage, reportAssignmentType]
        event_collector.drain.assert_called_once_with((save_world,))
        mock_logger.exception.assert_called_once_with(
            "Autosave failed after executing %r",
            "createroute A B",
        )
        self.assertEqual(
            [call.args[0] for call in mock_print.call_args_list],
            ["Warning: autosave failed: disk full", "ok"],
        )

    def test_exec_line_prints_value_error_cleanly(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()

        factory.create.side_effect = ValueError("bad input")

        with patch("builtins.print") as mock_print:
            engine._exec_line("broken")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_not_called()
        mock_print.assert_called_once_with("Error: bad input")

    def test_exec_line_prints_permission_error_cleanly(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()

        factory.create.side_effect = PermissionError("forbidden")

        with patch("builtins.print") as mock_print:
            engine._exec_line("save state.json")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_not_called()
        mock_print.assert_called_once_with("Permission Error: forbidden")

    def test_exec_line_logs_and_prints_unexpected_exception(self) -> None:
        engine, factory, _auth, _authz, _save_world, advance = self.make_engine()

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = False
        cmd.mutates_session = False
        cmd.autosaves_state = False
        cmd.execute.side_effect = RuntimeError("boom")
        factory.create.return_value = cmd

        with (
            patch("builtins.print") as mock_print,
            patch("src.adapters.driving.cli.engine.logger") as mock_logger,
        ):
            engine._exec_line("viewallroutes")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        mock_logger.exception.assert_called_once_with(
            "Unexpected CLI error while executing %r",
            "viewallroutes",
        )
        mock_print.assert_called_once_with("Unexpected error: boom")

    def test_exec_line_does_not_autosave_mutating_command_when_autosave_disabled(self) -> None:
        engine, factory, _auth, _authz, save_world, advance = self.make_engine(autosave_enabled=False)

        cmd = MagicMock()
        cmd.skips_heartbeat = False
        cmd.mutates_state = True
        cmd.mutates_session = False
        cmd.autosaves_state = True
        cmd.execute.return_value = "Loaded state."
        factory.create.return_value = cmd

        with patch("builtins.print") as mock_print:
            engine._exec_line("load state.json")  # pyright: ignore[reportPrivateUsage]

        advance.execute.assert_called_once_with()
        cmd.execute.assert_called_once_with()
        save_world.execute.assert_not_called()
        mock_print.assert_called_once_with("Loaded state.")

    def test_start_retries_invalid_main_menu_choice_before_exiting(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.input", side_effect=["unknown", "0"]),
            patch("builtins.print") as mock_print,
        ):
            engine.start()

        self.assertFalse(engine._running)  # pyright: ignore[reportPrivateUsage]
        self.assertIn(
            "Invalid option. Type a number from the menu, or 'cmd' for command mode.",
            [call.args[0] for call in mock_print.call_args_list],
        )
        self.assertIn("Goodbye!", [call.args[0] for call in mock_print.call_args_list])

    def test_menu_packages_retries_invalid_choice(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.input", side_effect=["unknown", "0"]),
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.print") as mock_print,
        ):
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_not_called()
        self.assertIn("Invalid option.", [call.args[0] for call in mock_print.call_args_list])

    def test_menu_state_quotes_save_paths_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["1", "my state file.json", "0"]),
        ):
            engine._menu_state()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("save 'my state file.json'")

    def test_menu_state_quotes_load_paths_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["2", "snapshots/world state.json", "0"]),
        ):
            engine._menu_state()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("load 'snapshots/world state.json'")

    def test_menu_state_supports_command_mode_shortcut(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_command_mode") as mock_command_mode,
            patch("builtins.input", side_effect=["cmd", "0"]),
        ):
            engine._menu_state()  # pyright: ignore[reportPrivateUsage]

        mock_command_mode.assert_called_once_with()

    def test_menu_state_reprompts_from_menu_after_blank_path(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.input", side_effect=["1", "", "0"]),
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.print") as mock_print,
        ):
            engine._menu_state()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_not_called()
        self.assertIn("No file name entered.", [call.args[0] for call in mock_print.call_args_list])

    def test_menu_trucks_dispatches_view_all_action(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.input", side_effect=["1", "0"]),
            patch.object(engine, "_exec_line") as mock_exec_line,
        ):
            engine._menu_trucks()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("viewalltrucks")

    def test_menu_audits_dispatches_view_logs_action(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch("builtins.input", side_effect=["1", "0"]),
            patch.object(engine, "_view_audits") as mock_view_audits,
        ):
            engine._menu_audits()  # pyright: ignore[reportPrivateUsage]

        mock_view_audits.assert_called_once_with()

    def test_view_audits_builds_option_command_from_prompts(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch(
                "builtins.input",
                side_effect=[
                    "PackageCreated",
                    "package",
                    "42",
                    "created",
                    "7",
                    "Alice Smith",
                    "CLI",
                    "2026-07-09 10:00",
                    "",
                    "",
                    "",
                    "25",
                    "5",
                    "yes",
                ],
            ),
        ):
            engine._view_audits()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with(
            "viewauditlogs --event_type PackageCreated --resource_type package --resource_id 42 "
            "--action created --actor_user_id 7 --actor_username 'Alice Smith' --source CLI "
            "--occurred_from '2026-07-09 10:00' --limit 25 --offset 5 --total"
        )

    def test_view_audits_rejects_total_without_limit(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.print") as mock_print,
            patch("builtins.input", side_effect=[""] * 13 + ["y"]),
        ):
            engine._view_audits()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_not_called()
        mock_print.assert_called_once_with("Include total requires a limit.")

    def test_menu_packages_quotes_customer_name_with_spaces(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch(
                "builtins.input",
                side_effect=["1", "SYD", "MEL", "10.5", "Mary Jane", "mary@example.com", "0412345678", "0"],
            ),
        ):
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with(
            "createpackage SYD MEL 10.5 'Mary Jane' mary@example.com 0412345678"
        )

    def test_menu_packages_quotes_remove_and_view_ids(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["2", "pkg 42", "5", "pkg 99", "0"]),
        ):
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

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
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("findsuitableroutesforpackage 'pkg 77'")

    def test_menu_packages_splits_assign_package_ids(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["3", "route-1", "pkg1 pkg2", "0"]),
        ):
            engine._menu_packages()  # pyright: ignore[reportPrivateUsage]

        mock_exec_line.assert_called_once_with("assignpackagestoroute route-1 pkg1 pkg2")

    def test_menu_routes_quotes_departure_timestamp(self) -> None:
        engine, _factory, _auth, _authz, _save_world, _advance = self.make_engine()

        with (
            patch.object(engine, "_exec_line") as mock_exec_line,
            patch("builtins.input", side_effect=["1", "SYD MEL", "2025-10-12 06:00", "0"]),
        ):
            engine._menu_routes()  # pyright: ignore[reportPrivateUsage]

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
            engine._menu_routes()  # pyright: ignore[reportPrivateUsage]

        self.assertEqual(
            [call.args[0] for call in mock_exec_line.call_args_list],
            [
                "viewroute 'route 1'",
                "removeroute 'route 2'",
                "assigntrucktoroute 'truck 4' 'route 5'",
                "findsuitabletrucksforroute 'route 6'",
            ],
        )
