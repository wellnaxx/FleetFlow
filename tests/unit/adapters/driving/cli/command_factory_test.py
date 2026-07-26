import unittest
from types import SimpleNamespace
from typing import cast
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory
from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview


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

    def test_container_backed_commands_receive_params_and_use_case(self) -> None:
        factory, container = self.make_factory()
        cases: list[tuple[str, str, list[str], object]] = [
            ("save state.json", "save", ["state.json"], container.state_cases.save),
            ("load state.json", "load", ["state.json"], container.state_cases.load),
            ("login alice", "login", ["alice"], container.auth_cases.login),
            ("logout", "logout", [], container.auth_cases.logout),
            ("whoami", "whoami", [], container.auth_cases.who_am_i),
            (
                "registeruser alice employee Alice",
                "registeruser",
                ["alice", "employee", "Alice"],
                container.auth_cases.register_user,
            ),
            ("changepassword alice", "changepassword", ["alice"], container.auth_cases.change_password),
            (
                'createpackage "SYD" "MEL" 5 "Alice"',
                "createpackage",
                ["SYD", "MEL", "5", "Alice"],
                container.package_cases.create,
            ),
            ("viewpackage 42", "viewpackage", ["42"], container.package_cases.view),
            ("viewallpackages", "viewallpackages", [], container.package_cases.view_all),
            ("removepackage 42", "removepackage", ["42"], container.package_cases.remove),
            (
                "viewunassignedpackages",
                "viewunassignedpackages",
                [],
                container.package_cases.view_unassigned,
            ),
            ("viewallcustomers", "viewallcustomers", [], container.customer_cases.view_all),
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
            (
                "getfleetoverview 25",
                "getfleetoverview",
                ["25"],
                container.fleet_cases.get_overview,
            ),
        ]

        for raw_input, command_name, params, expected_use_case in cases:
            del expected_use_case
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

    def test_get_fleet_overview_receives_registered_use_case_and_collector(self) -> None:
        """Build the fleet command from its typed container use-case group."""
        factory, container = self.make_factory()

        command = cast(GetFleetOverview, factory.create("getfleetoverview 25"))

        self.assertIsInstance(command, GetFleetOverview)
        self.assertEqual(command.params, ("25",))
        self.assertIs(command.use_case, container.fleet_cases.get_overview)
        self.assertIs(command.event_collector, container.event_collector)
