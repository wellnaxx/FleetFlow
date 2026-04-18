import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory


class _DummyCmd:
    """Minimal command class compatible with legacy BaseCommand signature."""

    def __init__(self, params: Any, app_data: Any, auth: Any) -> None:
        self._params = params
        self._app_data = app_data
        self._auth = auth

    def execute(self) -> str:
        return f"ok:{self._params!r}"


class CommandFactory_Should(unittest.TestCase):
    def make_factory(
        self,
    ) -> tuple[CommandFactory, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
        app = SimpleNamespace(name="app1")
        auth = SimpleNamespace(name="auth1")
        container = SimpleNamespace(create_package_use_case=MagicMock())
        factory = CommandFactory(data=app, auth=auth, container=container)  # type: ignore[reportArgumentType]
        return factory, app, auth, container

    def test_no_command_given_raises(self) -> None:
        cf, *_ = self.make_factory()
        with self.assertRaises(ValueError) as ctx:
            cf.create("   ")
        self.assertIn("No command given", str(ctx.exception))

    def test_unknown_command_raises(self) -> None:
        cf, *_ = self.make_factory()
        with self.assertRaises(ValueError) as ctx:
            cf.create("doesnotexist arg1 arg2")
        self.assertIn("Invalid command name: doesnotexist", str(ctx.exception))

    def test_case_insensitive_name_and_param_parsing_with_quotes(self) -> None:
        cf, app, auth, _container = self.make_factory()
        with patch("src.adapters.driving.cli.command_factory._LEGACY_REGISTRY", {"dummy": _DummyCmd}):
            cmd = cf.create('DuMmY "SYD" MEL "John Doe" "email with space@x.com"')
            self.assertIsInstance(cmd, _DummyCmd)
            self.assertEqual(cmd._params, ["SYD", "MEL", "John Doe", "email with space@x.com"])  # type: ignore[reportPrivateUsage]
            self.assertIs(cmd._app_data, app)  # type: ignore[reportPrivateUsage]
            self.assertIs(cmd._auth, auth)  # type: ignore[reportPrivateUsage]

    def test_extra_whitespace_and_simple_params(self) -> None:
        cf, *_ = self.make_factory()
        with patch("src.adapters.driving.cli.command_factory._LEGACY_REGISTRY", {"dummy": _DummyCmd}):
            cmd = cf.create("   dummy   A   B   C   ")
            self.assertEqual(cmd._params, ["A", "B", "C"])  # type: ignore[reportPrivateUsage]

    def test_update_app_replaces_app_reference_for_future_commands(self) -> None:
        cf, _app1, auth1, _container = self.make_factory()
        app2 = SimpleNamespace(name="app2")
        cf.update_app(app2)  # type: ignore[reportArgumentType]

        with patch("src.adapters.driving.cli.command_factory._LEGACY_REGISTRY", {"dummy": _DummyCmd}):
            cmd = cf.create("dummy X")
            self.assertIs(cmd._app_data, app2)  # type: ignore[reportPrivateUsage]
            self.assertIs(cmd._auth, auth1)  # type: ignore[reportPrivateUsage]

    def test_createpackage_uses_create_package_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        with patch("src.adapters.driving.cli.command_factory.CreatePackage") as create_package_cls:
            sentinel_cmd = object()
            create_package_cls.return_value = sentinel_cmd

            result = cf.create('createpackage "SYD" "MEL" 5 "Alice"')

            self.assertIs(result, sentinel_cmd)
            create_package_cls.assert_called_once_with(
                ["SYD", "MEL", "5", "Alice"],
                app,
                auth,
                container.create_package_use_case,
            )