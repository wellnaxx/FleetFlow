import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.commands.assign_packages_to_route import AssignPackagesToRoute
from src.adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute
from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from src.adapters.driving.cli.commands.auth_login import AuthLogin
from src.adapters.driving.cli.commands.auth_logout import AuthLogout
from src.adapters.driving.cli.commands.auth_register import AuthRegisterUser
from src.adapters.driving.cli.commands.auth_reset_password import AuthResetPassword
from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from src.adapters.driving.cli.commands.create_package import CreatePackage
from src.adapters.driving.cli.commands.create_route import CreateRoute
from src.adapters.driving.cli.commands.find_suitable_routes_for_package import (
    FindSuitableRoutesForPackage,
)
from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import (
    FindSuitableTrucksForRoute,
)
from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview
from src.adapters.driving.cli.commands.load_state import LoadState
from src.adapters.driving.cli.commands.remove_package import RemovePackage
from src.adapters.driving.cli.commands.remove_route import RemoveRoute
from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.adapters.driving.cli.commands.view_audits import ViewAuditLogs
from src.adapters.driving.cli.commands.view_package import ViewPackage
from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages


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
            ("save state.json", "save", ["state.json"], container.command_bus),
            ("load state.json", "load", ["state.json"], container.command_bus),
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
            ("viewpackage 42", "viewpackage", ["42"], container.query_bus),
            ("viewallpackages", "viewallpackages", [], container.query_bus),
            ("removepackage 42", "removepackage", ["42"], container.command_bus),
            (
                "viewunassignedpackages",
                "viewunassignedpackages",
                [],
                container.query_bus,
            ),
            ("viewallcustomers", "viewallcustomers", [], container.query_bus),
            (
                'createroute "SYD" "MEL" "2025-10-12" "06:00"',
                "createroute",
                ["SYD", "MEL", "2025-10-12", "06:00"],
                container.command_bus,
            ),
            ("viewroute 42", "viewroute", ["42"], container.query_bus),
            ("viewallroutes", "viewallroutes", [], container.query_bus),
            ("viewroutesinprogress", "viewroutesinprogress", [], container.query_bus),
            ("removeroute 42", "removeroute", ["42"], container.command_bus),
            (
                "assigntrucktoroute 11 22",
                "assigntrucktoroute",
                ["11", "22"],
                container.command_bus,
            ),
            (
                "findsuitabletrucksforroute 15",
                "findsuitabletrucksforroute",
                ["15"],
                container.query_bus,
            ),
            (
                "findsuitableroutesforpackage 77",
                "findsuitableroutesforpackage",
                ["77"],
                container.query_bus,
            ),
            (
                "assignpackagestoroute 5 42 43",
                "assignpackagestoroute",
                ["5", "42", "43"],
                container.command_bus,
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

    def test_load_state_receives_registered_command_bus(self) -> None:
        """Build world-state loading with the container command bus."""
        factory, container = self.make_factory()

        command = cast(LoadState, factory.create("load world.json"))

        self.assertIsInstance(command, LoadState)
        self.assertEqual(command.params, ("world.json",))
        self.assertIs(command.command_bus, container.command_bus)

    def test_remove_route_receives_registered_command_bus(self) -> None:
        """Build route removal with the container command bus."""
        factory, container = self.make_factory()

        command = cast(RemoveRoute, factory.create("removeroute 42"))

        self.assertIsInstance(command, RemoveRoute)
        self.assertEqual(command.params, ("42",))
        self.assertIs(command.command_bus, container.command_bus)

    def test_assign_packages_to_route_receives_registered_command_bus(self) -> None:
        """Build route package assignment with the container command bus."""
        factory, container = self.make_factory()

        command = cast(AssignPackagesToRoute, factory.create("assignpackagestoroute 5 42 43"))

        self.assertIsInstance(command, AssignPackagesToRoute)
        self.assertEqual(command.params, ("5", "42", "43"))
        self.assertIs(command.command_bus, container.command_bus)

    def test_assign_truck_to_route_receives_registered_command_bus(self) -> None:
        """Build route truck assignment with the container command bus."""
        factory, container = self.make_factory()

        command = cast(AssignTruckToRoute, factory.create("assigntrucktoroute 11 22"))

        self.assertIsInstance(command, AssignTruckToRoute)
        self.assertEqual(command.params, ("11", "22"))
        self.assertIs(command.command_bus, container.command_bus)

    def test_create_route_receives_registered_command_bus(self) -> None:
        """Build route creation with the container command bus."""
        factory, container = self.make_factory()

        command = cast(CreateRoute, factory.create("createroute SYD MEL"))

        self.assertIsInstance(command, CreateRoute)
        self.assertEqual(command.params, ("SYD", "MEL"))
        self.assertIs(command.command_bus, container.command_bus)

    def test_view_all_packages_receives_registered_query_bus(self) -> None:
        """Build package listing with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewAllPackages, factory.create("viewallpackages"))

        self.assertIsInstance(command, ViewAllPackages)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_all_routes_receives_registered_query_bus(self) -> None:
        """Build route listing with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewAllRoutes, factory.create("viewallroutes"))

        self.assertIsInstance(command, ViewAllRoutes)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_route_receives_registered_query_bus(self) -> None:
        """Build route lookup with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewRoute, factory.create("viewroute 42"))

        self.assertIsInstance(command, ViewRoute)
        self.assertEqual(command.params, ("42",))
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_routes_in_progress_receives_registered_query_bus(self) -> None:
        """Build active-route listing with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewRoutesInProgress, factory.create("viewroutesinprogress"))

        self.assertIsInstance(command, ViewRoutesInProgress)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_package_receives_registered_query_bus(self) -> None:
        """Build package lookup with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewPackage, factory.create("viewpackage 42"))

        self.assertIsInstance(command, ViewPackage)
        self.assertEqual(command.params, ("42",))
        self.assertIs(command.query_bus, container.query_bus)

    def test_view_unassigned_packages_receives_registered_query_bus(self) -> None:
        """Build unassigned-package listing with the container query bus."""
        factory, container = self.make_factory()

        command = cast(ViewUnassignedPackages, factory.create("viewunassignedpackages"))

        self.assertIsInstance(command, ViewUnassignedPackages)
        self.assertEqual(command.params, ())
        self.assertIs(command.query_bus, container.query_bus)

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

    def test_find_suitable_routes_receives_registered_query_bus(self) -> None:
        """Build suitable-route lookup with the container query bus."""
        factory, container = self.make_factory()

        command = cast(
            FindSuitableRoutesForPackage,
            factory.create("findsuitableroutesforpackage 77"),
        )

        self.assertIsInstance(command, FindSuitableRoutesForPackage)
        self.assertEqual(command.params, ("77",))
        self.assertIs(command.query_bus, container.query_bus)

    def test_find_suitable_trucks_receives_registered_query_bus(self) -> None:
        """Build suitable-truck lookup with the container query bus."""
        factory, container = self.make_factory()

        command = cast(
            FindSuitableTrucksForRoute,
            factory.create("findsuitabletrucksforroute 15"),
        )

        self.assertIsInstance(command, FindSuitableTrucksForRoute)
        self.assertEqual(command.params, ("15",))
        self.assertIs(command.query_bus, container.query_bus)
