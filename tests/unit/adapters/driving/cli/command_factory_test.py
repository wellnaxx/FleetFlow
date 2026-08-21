import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from src.adapters.driving.cli.commands.auth_login import AuthLogin
from src.adapters.driving.cli.commands.auth_logout import AuthLogout
from src.adapters.driving.cli.commands.auth_register import AuthRegisterUser
from src.adapters.driving.cli.commands.auth_reset_password import AuthResetPassword
from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from src.adapters.driving.cli.commands.create_package import CreatePackage
from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview
from src.adapters.driving.cli.commands.remove_package import RemovePackage
from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from src.adapters.driving.cli.commands.view_audits import ViewAuditLogs


class CommandFactoryShould(unittest.TestCase):
    def make_factory(self) -> tuple[CommandFactory, SimpleNamespace]:
        container = SimpleNamespace(
            state_cases=SimpleNamespace(
                save=MagicMock(),
                load=MagicMock(),
            ),
            auth_cases=SimpleNamespace(
                login=MagicMock(),
                logout=MagicMock(),
                who_am_i=MagicMock(),
                register_user=MagicMock(),
                change_password=MagicMock(),
                reset_password=MagicMock(),
            ),
            package_cases=SimpleNamespace(
                create=MagicMock(),
                view=MagicMock(),
                view_all=MagicMock(),
                remove=MagicMock(),
                view_unassigned=MagicMock(),
            ),
            customer_cases=SimpleNamespace(
                view_all=MagicMock(),
            ),
            fleet_cases=SimpleNamespace(
                get_overview=MagicMock(),
            ),
            route_cases=SimpleNamespace(
                create=MagicMock(),
                view=MagicMock(),
                view_all=MagicMock(),
                view_in_progress=MagicMock(),
                remove=MagicMock(),
                assign_truck=MagicMock(),
                find_suitable_trucks=MagicMock(),
                find_suitable_routes=MagicMock(),
                assign_packages=MagicMock(),
            ),
            truck_cases=SimpleNamespace(
                view_all=MagicMock(),
            ),
            command_bus=MagicMock(),
            query_bus=MagicMock(),
            event_collector=MagicMock(),
        )
        factory = CommandFactory(container=container)  # type: ignore[reportArgumentType]
        return factory, container

    def test_no_command_given_raises(self) -> None:
        factory, *_ = self.make_factory()

        with self.assertRaises(ValueError) as ctx:
            factory.create("   ")

        self.assertIn("No command given", str(ctx.exception))

    def test_unknown_command_raises(self) -> None:
        factory, *_ = self.make_factory()

        with self.assertRaises(ValueError) as ctx:
            factory.create("doesnotexist arg1 arg2")

        self.assertIn("Invalid command name: doesnotexist", str(ctx.exception))

    def test_case_insensitive_name_and_param_parsing_with_quotes(self) -> None:
        factory, container = self.make_factory()
        sentinel_cmd = object()
        builder = MagicMock(return_value=sentinel_cmd)

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewpackage": builder},
            clear=False,
        ):
            result = factory.create('ViEwPaCkAgE "42  "')

        self.assertIs(result, sentinel_cmd)
        builder.assert_called_once_with(container, ("42  ",))

    def test_container_backed_commands_receive_parsed_params(self) -> None:
        factory, container = self.make_factory()
        cases: list[tuple[str, str, list[str], object]] = [
            ("save state.json", "save", ["state.json"], container.state_cases.save),
            ("load state.json", "load", ["state.json"], container.state_cases.load),
            ("login alice", "login", ["alice"], container.command_bus),
            ("logout", "logout", [], container.command_bus),
            ("whoami", "whoami", [], container.query_bus),
            (
                "registeruser alice employee Alice",
                "registeruser",
                ["alice", "employee", "Alice"],
                container.command_bus,
            ),
            ("changepassword", "changepassword", [], container.command_bus),
            ("resetpassword alice", "resetpassword", ["alice"], container.command_bus),
            (
                'createpackage "SYD" "MEL" 5 "Alice"',
                "createpackage",
                ["SYD", "MEL", "5", "Alice"],
                container.command_bus,
            ),
            ("viewpackage 42", "viewpackage", ["42"], container.package_cases.view),
            ("viewallpackages", "viewallpackages", [], container.package_cases.view_all),
            ("removepackage 42", "removepackage", ["42"], container.command_bus),
            (
                "viewunassignedpackages",
                "viewunassignedpackages",
                [],
                container.package_cases.view_unassigned,
            ),
            ("viewallcustomers", "viewallcustomers", [], container.query_bus),
            (
                'createroute "SYD" "MEL" "2025-10-12" "06:00"',
                "createroute",
                ["SYD", "MEL", "2025-10-12", "06:00"],
                container.route_cases.create,
            ),
            ("viewroute 42", "viewroute", ["42"], container.route_cases.view),
            ("viewallroutes", "viewallroutes", [], container.route_cases.view_all),
            ("viewroutesinprogress", "viewroutesinprogress", [], container.route_cases.view_in_progress),
            ("removeroute 42", "removeroute", ["42"], container.route_cases.remove),
            (
                "assigntrucktoroute 11 22",
                "assigntrucktoroute",
                ["11", "22"],
                container.route_cases.assign_truck,
            ),
            (
                "findsuitabletrucksforroute 15",
                "findsuitabletrucksforroute",
                ["15"],
                container.route_cases.find_suitable_trucks,
            ),
            (
                "findsuitableroutesforpackage 77",
                "findsuitableroutesforpackage",
                ["77"],
                container.route_cases.find_suitable_routes,
            ),
            (
                "assignpackagestoroute 5 42 43",
                "assignpackagestoroute",
                ["5", "42", "43"],
                container.route_cases.assign_packages,
            ),
            ("viewalltrucks", "viewalltrucks", [], container.truck_cases.view_all),
            ("viewauditlogs", "viewauditlogs", [], container.query_bus),
            (
                "getfleetoverview 25",
                "getfleetoverview",
                ["25"],
                container.query_bus,
            ),
        ]

        for raw_input, command_name, params, expected_dependency in cases:
            del expected_dependency
            with self.subTest(command_name=command_name):
                sentinel_cmd = object()
                builder = MagicMock(return_value=sentinel_cmd)

                with patch.dict(
                    "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
                    {command_name: builder},
                    clear=False,
                ):
                    result = factory.create(raw_input)

                self.assertIs(result, sentinel_cmd)
                builder.assert_called_once_with(container, tuple(params))

    def test_who_am_i_receives_registered_query_bus(self) -> None:
        """Build the migrated WhoAmI command with the container query bus."""
        factory, container = self.make_factory()

        command = cast(AuthWhoAmI, factory.create("whoami"))

        self.assertIsInstance(command, AuthWhoAmI)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

    def test_change_password_receives_registered_command_bus(self) -> None:
        """Build the migrated password-change command with the command bus."""
        factory, container = self.make_factory()

        command = cast(AuthChangePassword, factory.create("changepassword"))

        self.assertIsInstance(command, AuthChangePassword)
        self.assertEqual(command.params, ())
        self.assertIs(command.command_bus, container.command_bus)

    def test_login_receives_registered_command_bus(self) -> None:
        """Build the migrated login command with the public command bus."""
        factory, container = self.make_factory()

        command = cast(AuthLogin, factory.create("login alice"))

        self.assertIsInstance(command, AuthLogin)
        self.assertEqual(command.params, ("alice",))
        self.assertIs(command.command_bus, container.command_bus)

    def test_logout_receives_registered_command_bus(self) -> None:
        """Build the migrated logout command with the command bus."""
        factory, container = self.make_factory()

        command = cast(AuthLogout, factory.create("logout"))

        self.assertIsInstance(command, AuthLogout)
        self.assertEqual(command.params, ())
        self.assertIs(command.command_bus, container.command_bus)

    def test_register_user_receives_registered_command_bus(self) -> None:
        """Build registration with the container command bus."""
        factory, container = self.make_factory()

        command = cast(AuthRegisterUser, factory.create("registeruser alice employee Alice"))

        self.assertIsInstance(command, AuthRegisterUser)
        self.assertEqual(command.params, ("alice", "employee", "Alice"))
        self.assertIs(command.command_bus, container.command_bus)

    def test_reset_password_receives_registered_command_bus(self) -> None:
        """Build administrative reset with the container command bus."""
        factory, container = self.make_factory()

        command = cast(AuthResetPassword, factory.create("resetpassword alice"))

        self.assertIsInstance(command, AuthResetPassword)
        self.assertEqual(command.params, ("alice",))
        self.assertIs(command.command_bus, container.command_bus)

    def test_create_package_receives_registered_command_bus(self) -> None:
        """Build package creation with the container command bus."""
        factory, container = self.make_factory()

        command = cast(CreatePackage, factory.create("createpackage SYD MEL 5 Alice"))

        self.assertIsInstance(command, CreatePackage)
        self.assertEqual(command.params, ("SYD", "MEL", "5", "Alice"))
        self.assertIs(command.command_bus, container.command_bus)

    def test_remove_package_receives_registered_command_bus(self) -> None:
        """Build package removal with the container command bus."""
        factory, container = self.make_factory()

        command = cast(RemovePackage, factory.create("removepackage 42"))

        self.assertIsInstance(command, RemovePackage)
        self.assertEqual(command.params, ("42",))
        self.assertIs(command.command_bus, container.command_bus)

    def test_view_audit_logs_receives_registered_query_bus(self) -> None:
        """Build the migrated audit command with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewAuditLogs, factory.create("viewauditlogs --limit 10"))

        self.assertIsInstance(command, ViewAuditLogs)
        self.assertEqual(command.params, ("--limit", "10"))
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_all_customers_receives_registered_query_bus(self) -> None:
        """Build customer listing with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewAllCustomers, factory.create("viewallcustomers"))

        self.assertIsInstance(command, ViewAllCustomers)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

    def test_get_fleet_overview_receives_registered_query_bus(self) -> None:
        """Build the fleet command with the container query bus."""
        factory, container = self.make_factory()

        command = cast(GetFleetOverview, factory.create("getfleetoverview 25"))

        self.assertIsInstance(command, GetFleetOverview)
        self.assertEqual(command.params, ("25",))
        self.assertIs(command.query_bus, container.query_bus)
