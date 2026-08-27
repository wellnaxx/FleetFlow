import unittest
from types import SimpleNamespace
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import cli_main
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand
from src.application.enums.event_sources import EventSource
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.eventing.current_context import get_event_context, get_optional_event_context
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStateRuntimeSwapError,
)
from src.domain.enums.auth import Role

if TYPE_CHECKING:
    from src.application.eventing.context import EventContext


def _container(*, autosave_enabled: bool = True, default_path: str = "state.json") -> MagicMock:
    container = MagicMock()
    container.auth = MagicMock()
    container.authz = MagicMock()
    container.autosave_enabled = autosave_enabled
    container.default_world_state_path = default_path
    return container


class MainStartupTests(unittest.TestCase):
    def assert_default_load_dispatched(self, container: MagicMock) -> None:
        """Assert startup requested the configured default snapshot through the bus."""
        container.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )

    def _run_main(self, container: MagicMock, *, exists: bool) -> SimpleNamespace:
        user_repo = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        with (
            patch("cli_main.os.path.exists", return_value=exists) as exists_mock,
            patch("cli_main.get_container", return_value=container) as get_container,
            patch("cli_main.get_user_repository", return_value=user_repo) as get_user_repository,
            patch("cli_main.bootstrap_admin") as bootstrap_admin,
            patch("cli_main.CommandFactory", return_value=command_factory) as command_factory_cls,
            patch("cli_main.Engine", return_value=engine) as engine_cls,
        ):
            cli_main.main()

        return SimpleNamespace(
            exists=exists_mock,
            get_container=get_container,
            get_user_repository=get_user_repository,
            user_repo=user_repo,
            bootstrap_admin=bootstrap_admin,
            command_factory_cls=command_factory_cls,
            command_factory=command_factory,
            engine_cls=engine_cls,
            engine=engine,
        )

    def test_main_binds_one_startup_context_and_clears_it_before_engine_start(self) -> None:
        container = _container(default_path="state.json")
        observed_contexts: list[EventContext] = []
        user_repo = MagicMock()
        engine = MagicMock()

        def get_container() -> MagicMock:
            observed_contexts.append(get_event_context())
            return container

        def get_user_repository() -> MagicMock:
            observed_contexts.append(get_event_context())
            return user_repo

        def bootstrap_admin(_auth: MagicMock, _store: MagicMock) -> None:
            observed_contexts.append(get_event_context())

        def load_default_state(*, key: object, command: object) -> None:
            self.assertIs(key, LOAD_WORLD)
            self.assertEqual(command, LoadWorldCommand(path="state.json"))
            observed_contexts.append(get_event_context())

        def start_engine() -> None:
            self.assertIsNone(get_optional_event_context())

        container.command_bus.dispatch.side_effect = load_default_state
        engine.start.side_effect = start_engine

        with (
            patch("cli_main.os.path.exists", return_value=True),
            patch("cli_main.get_container", side_effect=get_container),
            patch("cli_main.get_user_repository", side_effect=get_user_repository),
            patch("cli_main.bootstrap_admin", side_effect=bootstrap_admin),
            patch("cli_main.CommandFactory"),
            patch("cli_main.Engine", return_value=engine),
        ):
            cli_main.main()

        self.assertEqual(len(observed_contexts), 4)
        self.assertTrue(all(context is observed_contexts[0] for context in observed_contexts))
        self.assertIs(observed_contexts[0].source, EventSource.STARTUP)
        self.assertIsNone(observed_contexts[0].actor)
        engine.start.assert_called_once_with()
        self.assertIsNone(get_optional_event_context())

    def test_main_clears_startup_context_when_bootstrap_fails(self) -> None:
        container = _container()
        observed_contexts: list[EventContext] = []

        def get_container() -> MagicMock:
            observed_contexts.append(get_event_context())
            return container

        def fail_bootstrap(_auth: MagicMock, _store: MagicMock) -> None:
            observed_contexts.append(get_event_context())
            raise RuntimeError("bootstrap failed")

        with (
            patch("cli_main.get_container", side_effect=get_container),
            patch("cli_main.get_user_repository", return_value=MagicMock()),
            patch("cli_main.bootstrap_admin", side_effect=fail_bootstrap),
            patch("cli_main.CommandFactory") as command_factory,
            patch("cli_main.Engine") as engine,
            self.assertRaisesRegex(RuntimeError, "bootstrap failed"),
        ):
            cli_main.main()

        self.assertEqual(len(observed_contexts), 2)
        self.assertTrue(all(context is observed_contexts[0] for context in observed_contexts))
        self.assertIs(observed_contexts[0].source, EventSource.STARTUP)
        self.assertIsNone(get_optional_event_context())
        command_factory.assert_not_called()
        engine.assert_not_called()

    def test_main_skips_world_state_load_when_autosave_missing(self) -> None:
        container = _container(default_path="state.json")

        result = self._run_main(container, exists=False)

        result.bootstrap_admin.assert_called_once_with(container.auth, result.user_repo)
        container.command_bus.dispatch.assert_not_called()
        result.engine.start.assert_called_once_with()

    def test_main_loads_world_state_when_autosave_exists_and_is_valid(self) -> None:
        container = _container(default_path="state.json")

        result = self._run_main(container, exists=True)

        self.assert_default_load_dispatched(container)
        result.engine.start.assert_called_once_with()

    def test_main_treats_missing_default_world_state_as_noop_even_after_exists_check(self) -> None:
        container = _container(default_path="state.json")
        container.command_bus.dispatch.side_effect = WorldStateFileNotFoundError("missing")

        with (
            patch("cli_main.print") as print_mock,
            patch("cli_main._quarantine_corrupt_world_state") as quarantine,
        ):
            result = self._run_main(container, exists=True)

        container.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )
        quarantine.assert_not_called()
        print_mock.assert_not_called()
        result.engine.start.assert_called_once_with()

    def test_main_warns_quarantines_and_continues_when_default_world_state_is_corrupt(self) -> None:
        container = _container(default_path="state.json")
        container.command_bus.dispatch.side_effect = WorldStateCorruptionError(
            "bad snapshot",
            reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
        )

        with (
            patch("cli_main.print") as print_mock,
            patch(
                "cli_main._quarantine_corrupt_world_state",
                return_value="state.json.corrupt.2026-04-22T18-14-03",
            ) as quarantine,
            patch("cli_main.logger") as logger,
        ):
            result = self._run_main(container, exists=True)

        self.assert_default_load_dispatched(container)
        logger.exception.assert_called_once_with(
            "Failed to load default world state from %r.",
            "state.json",
        )
        quarantine.assert_called_once_with("state.json")
        print_mock.assert_called_once()

        warning_text = print_mock.call_args.args[0]
        self.assertIn("WARNING: Saved world state could not be loaded", warning_text)
        self.assertIn("Starting with empty state.", warning_text)
        self.assertIn("Quarantined file: state.json.corrupt.2026-04-22T18-14-03", warning_text)
        result.engine.start.assert_called_once_with()

    def test_main_warns_and_continues_when_default_world_state_is_corrupt_and_quarantine_fails(
        self,
    ) -> None:
        container = _container(default_path="state.json")
        container.command_bus.dispatch.side_effect = WorldStateCorruptionError(
            "bad snapshot",
            reason=WorldStateCorruptionReason.INVARIANT_VIOLATION,
        )

        with (
            patch("cli_main.print") as print_mock,
            patch("cli_main._quarantine_corrupt_world_state", return_value=None) as quarantine,
            patch("cli_main.logger") as logger,
        ):
            result = self._run_main(container, exists=True)

        self.assert_default_load_dispatched(container)
        logger.exception.assert_called_once_with(
            "Failed to load default world state from %r.",
            "state.json",
        )
        quarantine.assert_called_once_with("state.json")
        print_mock.assert_called_once()

        warning_text = print_mock.call_args.args[0]
        self.assertIn("WARNING: Saved world state could not be loaded.", warning_text)
        self.assertIn("Starting with empty state.", warning_text)
        self.assertIn("could not be moved aside automatically", warning_text)
        result.engine.start.assert_called_once_with()

    def test_main_does_not_quarantine_non_corruption_startup_errors(self) -> None:
        container = _container(default_path="state.json")
        container.command_bus.dispatch.side_effect = RuntimeError("runtime bug")

        with (
            patch("cli_main.print") as print_mock,
            patch("cli_main._quarantine_corrupt_world_state") as quarantine,
            patch("cli_main.os.path.exists", return_value=True),
            patch("cli_main.get_container", return_value=container),
            patch("cli_main.get_user_repository", return_value=MagicMock()),
            patch("cli_main.bootstrap_admin"),
            patch("cli_main.CommandFactory") as command_factory_cls,
            patch("cli_main.Engine") as engine_cls,
            self.assertRaises(RuntimeError),
        ):
            cli_main.main()

        quarantine.assert_not_called()
        print_mock.assert_not_called()
        command_factory_cls.assert_not_called()
        engine_cls.assert_not_called()

    def test_main_skips_default_world_state_load_when_autosave_disabled(self) -> None:
        container = _container(autosave_enabled=False, default_path="state.json")

        result = self._run_main(container, exists=True)

        result.exists.assert_not_called()
        container.command_bus.dispatch.assert_not_called()
        result.engine.start.assert_called_once_with()

    def test_main_wires_engine_with_container_dependencies(self) -> None:
        container = _container(default_path="state.json")

        result = self._run_main(container, exists=False)

        result.command_factory_cls.assert_called_once_with(container)
        result.engine_cls.assert_called_once_with(
            result.command_factory,
            container.auth,
            container.authz,
            "state.json",
            container.command_bus,
            True,
        )


class QuarantineCorruptWorldStateTests(unittest.TestCase):
    @patch("cli_main.os.replace")
    @patch("cli_main.datetime")
    def test_quarantine_corrupt_world_state_moves_file_and_returns_new_path(
        self,
        datetime_cls: MagicMock,
        replace: MagicMock,
    ) -> None:
        datetime_cls.now.return_value.strftime.return_value = "2026-04-22T18-14-03"

        original = "C:/fake/state.json"
        quarantined = cli_main._quarantine_corrupt_world_state(original)  # pyright: ignore[reportPrivateUsage]

        expected = "C:/fake/state.json.corrupt.2026-04-22T18-14-03"
        self.assertEqual(quarantined, expected)
        replace.assert_called_once_with(original, expected)

    @patch("cli_main.logger")
    @patch("cli_main.os.replace", side_effect=OSError("locked"))
    @patch("cli_main.datetime")
    def test_quarantine_corrupt_world_state_returns_none_when_move_fails(
        self,
        datetime_cls: MagicMock,
        replace: MagicMock,
        logger: MagicMock,
    ) -> None:
        datetime_cls.now.return_value.strftime.return_value = "2026-04-22T18-14-03"

        original = "C:/fake/state.json"
        quarantined = cli_main._quarantine_corrupt_world_state(original)  # pyright: ignore[reportPrivateUsage]

        self.assertIsNone(quarantined)
        logger.exception.assert_called_once_with(
            "Failed to quarantine corrupt world state file %r.",
            original,
        )

    def test_main_does_not_quarantine_runtime_swap_errors(self) -> None:
        container = _container(default_path="state.json")
        container.command_bus.dispatch.side_effect = WorldStateRuntimeSwapError(
            "Failed to replace runtime world state."
        )

        with (
            patch("cli_main.print") as print_mock,
            patch("cli_main._quarantine_corrupt_world_state") as quarantine,
            patch("cli_main.os.path.exists", return_value=True),
            patch("cli_main.get_container", return_value=container),
            patch("cli_main.get_user_repository", return_value=MagicMock()),
            patch("cli_main.bootstrap_admin"),
            patch("cli_main.CommandFactory") as command_factory_cls,
            patch("cli_main.Engine") as engine_cls,
            self.assertRaises(WorldStateRuntimeSwapError),
        ):
            cli_main.main()

        container.command_bus.dispatch.assert_called_once_with(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path="state.json"),
        )
        quarantine.assert_not_called()
        print_mock.assert_not_called()
        command_factory_cls.assert_not_called()
        engine_cls.assert_not_called()


class BootstrapAdminTests(unittest.TestCase):
    def test_bootstrap_admin_does_nothing_when_admin_exists(self) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get_by_username.return_value = object()

        cli_main.bootstrap_admin(auth, store)

        store.get_by_username.assert_called_once_with("admin")
        auth.register_user.assert_not_called()

    @patch("cli_main.getpass.getpass", side_effect=["Secret123!", "Secret123!"])
    @patch("cli_main.sys.stdin")
    def test_bootstrap_admin_prompts_and_creates_admin_interactively(
        self,
        stdin: MagicMock,
        getpass_mock: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get_by_username.return_value = None
        stdin.isatty.return_value = True

        cli_main.bootstrap_admin(auth, store)

        auth.register_user.assert_called_once_with(
            username="admin",
            role=Role.MANAGER,
            name="Admin",
            email="",
            phone_number="",
            password="Secret123!",
        )

    @patch("cli_main.sys.stdin")
    def test_bootstrap_admin_fails_cleanly_when_non_interactive_and_no_admin(
        self,
        stdin: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get_by_username.return_value = None
        stdin.isatty.return_value = False

        with self.assertRaises(RuntimeError) as ctx:
            cli_main.bootstrap_admin(auth, store)

        self.assertIn("No admin user exists", str(ctx.exception))
        auth.register_user.assert_not_called()

    @patch("cli_main.getpass.getpass", side_effect=["Secret123!", "Different123!"])
    @patch("cli_main.sys.stdin")
    def test_bootstrap_admin_rejects_password_confirmation_mismatch(
        self,
        stdin: MagicMock,
        getpass_mock: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get_by_username.return_value = None
        stdin.isatty.return_value = True

        with self.assertRaises(ValueError) as ctx:
            cli_main.bootstrap_admin(auth, store)

        self.assertIn("do not match", str(ctx.exception))
        auth.register_user.assert_not_called()
