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
    def test_main_aborts_when_world_state_load_fails(
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

        user_store_cls.return_value = store
        auth_service_cls.return_value = auth
        container_cls.return_value = container
        container.load_world_state_use_case.execute.side_effect = ValueError("bad snapshot")

        with self.assertRaises(SystemExit) as ctx:
            main.main()

        self.assertIn("Startup failed while loading world state", str(ctx.exception))
        self.assertIn("bad snapshot", str(ctx.exception))
        engine_cls.return_value.start.assert_not_called()
