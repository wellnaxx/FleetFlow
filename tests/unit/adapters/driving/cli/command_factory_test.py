import unittest
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory


def _get_create_package_use_case(container: Any) -> Any:
    return container.create_package_use_case


def _get_view_package_use_case(container: Any) -> Any:
    return container.view_package_use_case


def _get_view_all_packages_use_case(container: Any) -> Any:
    return container.view_all_packages_use_case


def _get_remove_package_use_case(container: Any) -> Any:
    return container.remove_package_use_case


def _get_view_unassigned_packages_use_case(container: Any) -> Any:
    return container.view_unassigned_packages_use_case


def _get_view_all_customers_use_case(container: Any) -> Any:
    return container.view_all_customers_use_case


def _get_create_route_use_case(container: Any) -> Any:
    return container.create_route_use_case


def _get_view_route_use_case(container: Any) -> Any:
    return container.view_route_use_case


def _get_view_all_routes_use_case(container: Any) -> Any:
    return container.view_all_routes_use_case


def _get_view_routes_in_progress_use_case(container: Any) -> Any:
    return container.view_routes_in_progress_use_case


def _get_remove_route_use_case(container: Any) -> Any:
    return container.remove_route_use_case


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
        container = SimpleNamespace(
            create_package_use_case=MagicMock(),
            view_package_use_case=MagicMock(),
            view_all_packages_use_case=MagicMock(),
            remove_package_use_case=MagicMock(),
            view_unassigned_packages_use_case=MagicMock(),
            view_all_customers_use_case=MagicMock(),
            create_route_use_case=MagicMock(),
            view_route_use_case=MagicMock(),
            view_all_routes_use_case=MagicMock(),
            view_routes_in_progress_use_case=MagicMock(),
            remove_route_use_case=MagicMock(),
        )
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

    def test_update_app_replaces_app_reference_for_future_legacy_commands(self) -> None:
        cf, _app1, auth1, _container = self.make_factory()
        app2 = SimpleNamespace(name="app2")
        cf.update_app(app2)  # type: ignore[reportArgumentType]

        with patch("src.adapters.driving.cli.command_factory._LEGACY_REGISTRY", {"dummy": _DummyCmd}):
            cmd = cf.create("dummy X")

            self.assertIs(cmd._app_data, app2)  # type: ignore[reportPrivateUsage]
            self.assertIs(cmd._auth, auth1)  # type: ignore[reportPrivateUsage]

    def test_createpackage_uses_create_package_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"createpackage": (cmd_cls, _get_create_package_use_case)},
            clear=False,
        ):
            result = cf.create('createpackage "SYD" "MEL" 5 "Alice"')

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["SYD", "MEL", "5", "Alice"],
            app,
            auth,
            container.create_package_use_case,
        )

    def test_viewpackage_uses_view_package_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewpackage": (cmd_cls, _get_view_package_use_case)},
            clear=False,
        ):
            result = cf.create("viewpackage 42")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["42"],
            app,
            auth,
            container.view_package_use_case,
        )

    def test_viewallpackages_uses_view_all_packages_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewallpackages": (cmd_cls, _get_view_all_packages_use_case)},
            clear=False,
        ):
            result = cf.create("viewallpackages")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            [],
            app,
            auth,
            container.view_all_packages_use_case,
        )

    def test_removepackage_uses_remove_package_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"removepackage": (cmd_cls, _get_remove_package_use_case)},
            clear=False,
        ):
            result = cf.create("removepackage 42")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["42"],
            app,
            auth,
            container.remove_package_use_case,
        )

    def test_viewunassignedpackages_uses_view_unassigned_packages_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewunassignedpackages": (cmd_cls, _get_view_unassigned_packages_use_case)},
            clear=False,
        ):
            result = cf.create("viewunassignedpackages")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            [],
            app,
            auth,
            container.view_unassigned_packages_use_case,
        )

    def test_viewallcustomers_uses_view_all_customers_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewallcustomers": (cmd_cls, _get_view_all_customers_use_case)},
            clear=False,
        ):
            result = cf.create("viewallcustomers")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            [],
            app,
            auth,
            container.view_all_customers_use_case,
        )

    def test_createroute_uses_create_route_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"createroute": (cmd_cls, _get_create_route_use_case)},
            clear=False,
        ):
            result = cf.create('createroute "SYD" "MEL" "2025-10-12" "06:00"')

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["SYD", "MEL", "2025-10-12", "06:00"],
            app,
            auth,
            container.create_route_use_case,
        )

    def test_viewroute_uses_view_route_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewroute": (cmd_cls, _get_view_route_use_case)},
            clear=False,
        ):
            result = cf.create("viewroute 42")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["42"],
            app,
            auth,
            container.view_route_use_case,
        )

    def test_viewallroutes_uses_view_all_routes_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewallroutes": (cmd_cls, _get_view_all_routes_use_case)},
            clear=False,
        ):
            result = cf.create("viewallroutes")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            [],
            app,
            auth,
            container.view_all_routes_use_case,
        )

    def test_viewroutesinprogress_uses_view_routes_in_progress_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewroutesinprogress": (cmd_cls, _get_view_routes_in_progress_use_case)},
            clear=False,
        ):
            result = cf.create("viewroutesinprogress")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            [],
            app,
            auth,
            container.view_routes_in_progress_use_case,
        )

    def test_removeroute_uses_remove_route_use_case_from_container(self) -> None:
        cf, app, auth, container = self.make_factory()

        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"removeroute": (cmd_cls, _get_remove_route_use_case)},
            clear=False,
        ):
            result = cf.create("removeroute 42")

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(
            ["42"],
            app,
            auth,
            container.remove_route_use_case,
        )