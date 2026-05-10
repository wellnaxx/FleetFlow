import unittest
from unittest.mock import MagicMock, patch

import main
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStateRuntimeSwapError,
)
from src.domain.enums.auth import Role


class MainStartupTests(unittest.TestCase):
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=False)
    def test_main_skips_world_state_load_when_autosave_missing(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = main.DEFAULT_WORLD_STATE_PATH
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        main.main()

        container.load_world_state_use_case.execute.assert_not_called()
        engine.start.assert_called_once_with()

    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_loads_world_state_when_autosave_exists_and_is_valid(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with("state.json")
        engine.start.assert_called_once_with()

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_treats_missing_default_world_state_as_noop_even_after_exists_check(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
        quarantine: MagicMock,
        print_mock: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine
        container.load_world_state_use_case.execute.side_effect = WorldStateFileNotFoundError("missing")

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with("state.json")
        quarantine.assert_not_called()
        print_mock.assert_not_called()
        engine.start.assert_called_once_with()

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state", return_value="state.json.corrupt.2026-04-22T18-14-03")
    @patch("main.logger")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_warns_quarantines_and_continues_when_default_world_state_is_corrupt(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
        logger: MagicMock,
        quarantine: MagicMock,
        print_mock: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        container.load_world_state_use_case.execute.side_effect = WorldStateCorruptionError("bad snapshot")

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with("state.json")
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

        engine.start.assert_called_once_with()

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state", return_value=None)
    @patch("main.logger")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_warns_and_continues_when_default_world_state_is_corrupt_and_quarantine_fails(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
        logger: MagicMock,
        quarantine: MagicMock,
        print_mock: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        container.load_world_state_use_case.execute.side_effect = WorldStateCorruptionError("bad snapshot")

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with("state.json")
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

        engine.start.assert_called_once_with()

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_does_not_quarantine_non_corruption_startup_errors(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
        quarantine: MagicMock,
        print_mock: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        container.load_world_state_use_case.execute.side_effect = RuntimeError("runtime bug")

        with self.assertRaises(RuntimeError):
            main.main()

        quarantine.assert_not_called()
        print_mock.assert_not_called()
        command_factory_cls.assert_not_called()
        engine_cls.assert_not_called()

    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_skips_default_world_state_load_when_autosave_disabled(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()
        command_factory = MagicMock()
        engine = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = False
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        main.main()

        exists.assert_not_called()
        container.load_world_state_use_case.execute.assert_not_called()
        engine.start.assert_called_once_with()


class QuarantineCorruptWorldStateTests(unittest.TestCase):
    @patch("main.os.replace")
    @patch("main.datetime")
    def test_quarantine_corrupt_world_state_moves_file_and_returns_new_path(
        self,
        datetime_cls: MagicMock,
        replace: MagicMock,
    ) -> None:
        datetime_cls.now.return_value.strftime.return_value = "2026-04-22T18-14-03"

        original = "C:/fake/state.json"
        quarantined = main._quarantine_corrupt_world_state(original)  # pyright: ignore[reportPrivateUsage]

        expected = "C:/fake/state.json.corrupt.2026-04-22T18-14-03"
        self.assertEqual(quarantined, expected)
        replace.assert_called_once_with(original, expected)

    @patch("main.logger")
    @patch("main.os.replace", side_effect=OSError("locked"))
    @patch("main.datetime")
    def test_quarantine_corrupt_world_state_returns_none_when_move_fails(
        self,
        datetime_cls: MagicMock,
        replace: MagicMock,
        logger: MagicMock,
    ) -> None:
        datetime_cls.now.return_value.strftime.return_value = "2026-04-22T18-14-03"

        original = "C:/fake/state.json"
        quarantined = main._quarantine_corrupt_world_state(original)  # pyright: ignore[reportPrivateUsage]

        self.assertIsNone(quarantined)
        logger.exception.assert_called_once_with(
            "Failed to quarantine corrupt world state file %r.",
            original,
        )

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.build_container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.JSONUserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_does_not_quarantine_runtime_swap_errors(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        build_container: MagicMock,
        command_factory_cls: MagicMock,
        engine_cls: MagicMock,
        quarantine: MagicMock,
        print_mock: MagicMock,
    ) -> None:
        store = MagicMock()
        auth = MagicMock()
        container = MagicMock()

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container.autosave_enabled = True
        container.default_world_state_path = "state.json"
        build_container.return_value = container
        container.load_world_state_use_case.execute.side_effect = WorldStateRuntimeSwapError(
            "Failed to replace runtime world state."
        )

        with self.assertRaises(WorldStateRuntimeSwapError):
            main.main()

        container.load_world_state_use_case.execute.assert_called_once_with("state.json")
        quarantine.assert_not_called()
        print_mock.assert_not_called()
        command_factory_cls.assert_not_called()
        engine_cls.assert_not_called()


class BootstrapAdminTests(unittest.TestCase):
    def test_bootstrap_admin_does_nothing_when_admin_exists(self) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get.return_value = object()

        main.bootstrap_admin(auth, store)

        store.get.assert_called_once_with("admin")
        auth.register_user.assert_not_called()

    @patch("main.getpass.getpass", side_effect=["Secret123!", "Secret123!"])
    @patch("main.sys.stdin")
    def test_bootstrap_admin_prompts_and_creates_admin_interactively(
        self,
        stdin: MagicMock,
        getpass_mock: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get.return_value = None
        stdin.isatty.return_value = True

        main.bootstrap_admin(auth, store)

        auth.register_user.assert_called_once_with(
            username="admin",
            role=Role.MANAGER,
            name="Admin",
            email="",
            phone_number="",
            password="Secret123!",
        )

    @patch("main.sys.stdin")
    def test_bootstrap_admin_fails_cleanly_when_non_interactive_and_no_admin(
        self,
        stdin: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get.return_value = None
        stdin.isatty.return_value = False

        with self.assertRaises(RuntimeError) as ctx:
            main.bootstrap_admin(auth, store)

        self.assertIn("No admin user exists", str(ctx.exception))
        auth.register_user.assert_not_called()

    @patch("main.getpass.getpass", side_effect=["Secret123!", "Different123!"])
    @patch("main.sys.stdin")
    def test_bootstrap_admin_rejects_password_confirmation_mismatch(
        self,
        stdin: MagicMock,
        getpass_mock: MagicMock,
    ) -> None:
        auth = MagicMock()
        store = MagicMock()
        store.get.return_value = None
        stdin.isatty.return_value = True

        with self.assertRaises(ValueError) as ctx:
            main.bootstrap_admin(auth, store)

        self.assertIn("do not match", str(ctx.exception))
        auth.register_user.assert_not_called()
