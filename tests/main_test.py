import unittest
from unittest.mock import MagicMock, patch

import main


class MainStartupTests(unittest.TestCase):
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.Container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.UserStore")
    @patch("main.os.path.exists", return_value=False)
    def test_main_skips_world_state_load_when_autosave_missing(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        container_cls: MagicMock,
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
        container_cls.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        main.main()

        container.load_world_state_use_case.execute.assert_not_called()
        engine.start.assert_called_once_with()

    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.Container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.UserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_loads_world_state_when_autosave_exists_and_is_valid(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        container_cls: MagicMock,
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
        container_cls.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with(main.DEFAULT_WORLD_STATE_PATH)
        engine.start.assert_called_once_with()

    @patch("main.print")
    @patch("main._quarantine_corrupt_world_state", return_value="state.json.corrupt.2026-04-22T18-14-03")
    @patch("main.logger")
    @patch("main.Engine")
    @patch("main.CommandFactory")
    @patch("main.Container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.UserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_warns_quarantines_and_continues_when_world_state_load_fails(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        container_cls: MagicMock,
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
        container_cls.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        container.load_world_state_use_case.execute.side_effect = ValueError("bad snapshot")

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with(main.DEFAULT_WORLD_STATE_PATH)
        logger.exception.assert_called_once_with(
            "Failed to load default world state from %r.",
            main.DEFAULT_WORLD_STATE_PATH,
        )
        quarantine.assert_called_once_with(main.DEFAULT_WORLD_STATE_PATH)
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
    @patch("main.Container")
    @patch("main.bootstrap_admin")
    @patch("main.AuthService")
    @patch("main.UserStore")
    @patch("main.os.path.exists", return_value=True)
    def test_main_warns_and_continues_when_world_state_load_fails_and_quarantine_fails(
        self,
        exists: MagicMock,
        user_store_cls: MagicMock,
        auth_service_cls: MagicMock,
        bootstrap_admin: MagicMock,
        container_cls: MagicMock,
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
        container_cls.return_value = container
        command_factory_cls.return_value = command_factory
        engine_cls.return_value = engine

        container.load_world_state_use_case.execute.side_effect = ValueError("bad snapshot")

        main.main()

        container.load_world_state_use_case.execute.assert_called_once_with(main.DEFAULT_WORLD_STATE_PATH)
        logger.exception.assert_called_once_with(
            "Failed to load default world state from %r.",
            main.DEFAULT_WORLD_STATE_PATH,
        )
        quarantine.assert_called_once_with(main.DEFAULT_WORLD_STATE_PATH)
        print_mock.assert_called_once()

        warning_text = print_mock.call_args.args[0]
        self.assertIn("WARNING: Saved world state could not be loaded.", warning_text)
        self.assertIn("Starting with empty state.", warning_text)
        self.assertIn("could not be moved aside automatically", warning_text)

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
        quarantined = main._quarantine_corrupt_world_state(original) # pyright: ignore[reportPrivateUsage]

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
        quarantined = main._quarantine_corrupt_world_state(original) # pyright: ignore[reportPrivateUsage]

        self.assertIsNone(quarantined)
        logger.exception.assert_called_once_with(
            "Failed to quarantine corrupt world state file %r.",
            original,
        )
