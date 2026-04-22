import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from src.adapters.driving.cli.command_factory import CommandFactory


class CommandFactoryShould(unittest.TestCase):
    def make_factory(self) -> tuple[CommandFactory, SimpleNamespace, SimpleNamespace, SimpleNamespace]:
        auth = SimpleNamespace(name="auth1")
        authz = SimpleNamespace(name="authz1")
        container = SimpleNamespace(
            save_world_state_use_case=MagicMock(),
            load_world_state_use_case=MagicMock(),
            login_use_case=MagicMock(),
            logout_use_case=MagicMock(),
            who_am_i_use_case=MagicMock(),
            register_user_use_case=MagicMock(),
            change_password_use_case=MagicMock(),
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
            assign_truck_to_route_use_case=MagicMock(),
            find_suitable_trucks_for_route_use_case=MagicMock(),
            find_suitable_routes_for_package_use_case=MagicMock(),
            assign_packages_to_route_use_case=MagicMock(),
            view_all_trucks_use_case=MagicMock(),
        )
        factory = CommandFactory(auth=auth, authz=authz, container=container)  # type: ignore[reportArgumentType]
        return factory, auth, authz, container

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
        factory, auth, authz, container = self.make_factory()
        cmd_cls = MagicMock()
        sentinel_cmd = object()
        cmd_cls.return_value = sentinel_cmd

        with patch.dict(
            "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
            {"viewpackage": (cmd_cls, lambda c: c.view_package_use_case)},
            clear=False,
        ):
            result = factory.create('ViEwPaCkAgE "42  "')

        self.assertIs(result, sentinel_cmd)
        cmd_cls.assert_called_once_with(["42  "], auth, authz, container.view_package_use_case)

    def test_container_backed_commands_receive_auth_authz_and_use_case(self) -> None:
        factory, auth, authz, container = self.make_factory()
        cases = [
            ("save state.json", "save", ["state.json"], container.save_world_state_use_case),
            ("load state.json", "load", ["state.json"], container.load_world_state_use_case),
            ("login alice", "login", ["alice"], container.login_use_case),
            ("logout", "logout", [], container.logout_use_case),
            ("whoami", "whoami", [], container.who_am_i_use_case),
            ("registeruser alice employee Alice", "registeruser", ["alice", "employee", "Alice"], container.register_user_use_case),
            ("changepassword alice", "changepassword", ["alice"], container.change_password_use_case),
            ('createpackage "SYD" "MEL" 5 "Alice"', "createpackage", ["SYD", "MEL", "5", "Alice"], container.create_package_use_case),
            ("viewpackage 42", "viewpackage", ["42"], container.view_package_use_case),
            ("viewallpackages", "viewallpackages", [], container.view_all_packages_use_case),
            ("removepackage 42", "removepackage", ["42"], container.remove_package_use_case),
            ("viewunassignedpackages", "viewunassignedpackages", [], container.view_unassigned_packages_use_case),
            ("viewallcustomers", "viewallcustomers", [], container.view_all_customers_use_case),
            ('createroute "SYD" "MEL" "2025-10-12" "06:00"', "createroute", ["SYD", "MEL", "2025-10-12", "06:00"], container.create_route_use_case),
            ("viewroute 42", "viewroute", ["42"], container.view_route_use_case),
            ("viewallroutes", "viewallroutes", [], container.view_all_routes_use_case),
            ("viewroutesinprogress", "viewroutesinprogress", [], container.view_routes_in_progress_use_case),
            ("removeroute 42", "removeroute", ["42"], container.remove_route_use_case),
            ("assigntrucktoroute 11 22", "assigntrucktoroute", ["11", "22"], container.assign_truck_to_route_use_case),
            ("findsuitabletrucksforroute 15", "findsuitabletrucksforroute", ["15"], container.find_suitable_trucks_for_route_use_case),
            ("findsuitableroutesforpackage 77", "findsuitableroutesforpackage", ["77"], container.find_suitable_routes_for_package_use_case),
            ("assignpackagestoroute 5 42 43", "assignpackagestoroute", ["5", "42", "43"], container.assign_packages_to_route_use_case),
            ("viewalltrucks", "viewalltrucks", [], container.view_all_trucks_use_case),
        ]

        for raw_input, command_name, params, expected_use_case in cases:
            with self.subTest(command_name=command_name):
                cmd_cls = MagicMock()
                sentinel_cmd = object()
                cmd_cls.return_value = sentinel_cmd

                with patch.dict(
                    "src.adapters.driving.cli.command_factory._CONTAINER_COMMANDS",
                    {command_name: (cmd_cls, lambda _container, uc=expected_use_case: uc)},
                    clear=False,
                ):
                    result = factory.create(raw_input)

                self.assertIs(result, sentinel_cmd)
                cmd_cls.assert_called_once_with(params, auth, authz, expected_use_case)
