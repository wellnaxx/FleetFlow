"""Unit tests for command-to-use-case argument adaptation."""

import unittest
from datetime import datetime
from unittest.mock import MagicMock

from src.application.commands.auth.login import LoginCommand
from src.application.commands.auth.logout import LogoutCommand
from src.application.commands.auth.register_user import RegisterUserCommand
from src.application.commands.auth.reset_password import ResetUserPasswordCommand
from src.application.commands.packages.create_package import CreatePackageCommand
from src.application.commands.packages.remove_package import RemovePackageCommand
from src.application.commands.routes.assign_packages_to_route import AssignPackagesToRouteCommand
from src.application.commands.routes.assign_truck_to_route import AssignTruckToRouteCommand
from src.application.commands.routes.create_route import CreateRouteCommand
from src.application.commands.routes.remove_route import RemoveRouteCommand
from src.application.commands.state.load_world import LoadWorldCommand
from src.application.commands.state.save_world import SaveWorldCommand
from src.application.handlers.commands.auth.login import LoginCommandHandler
from src.application.handlers.commands.auth.logout import LogoutCommandHandler
from src.application.handlers.commands.auth.register_user import RegisterUserCommandHandler
from src.application.handlers.commands.auth.reset_password import ResetUserPasswordCommandHandler
from src.application.handlers.commands.packages.create_package import CreatePackageCommandHandler
from src.application.handlers.commands.packages.remove_package import RemovePackageCommandHandler
from src.application.handlers.commands.routes.assign_packages_to_route import (
    AssignPackagesToRouteCommandHandler,
)
from src.application.handlers.commands.routes.assign_truck_to_route import AssignTruckToRouteCommandHandler
from src.application.handlers.commands.routes.create_route import CreateRouteCommandHandler
from src.application.handlers.commands.routes.remove_route import RemoveRouteCommandHandler
from src.application.handlers.commands.state.load_world import LoadWorldCommandHandler
from src.application.handlers.commands.state.save_world import SaveWorldCommandHandler
from src.domain.enums.auth import Role

NOW = datetime(2026, 8, 6, 12, 30)


class CommandHandlersShould(unittest.TestCase):
    """Verify that command handlers delegate once with the intended arguments."""

    def test_login_delegates_credentials_and_returns_result(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = LoginCommandHandler(use_case).execute(LoginCommand(username="alex", password="secret"))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with("alex", "secret")

    def test_login_propagates_use_case_failure(self) -> None:
        use_case = MagicMock()
        failure = RuntimeError("login failed")
        use_case.execute.side_effect = failure

        with self.assertRaises(RuntimeError) as raised:
            LoginCommandHandler(use_case).execute(LoginCommand(username="alex", password="secret"))

        self.assertIs(raised.exception, failure)

    def test_logout_delegates_without_arguments(self) -> None:
        use_case = MagicMock()

        result = LogoutCommandHandler(use_case).execute(LogoutCommand())

        self.assertIsNone(result)
        use_case.execute.assert_called_once_with()

    def test_register_user_delegates_all_account_fields(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        command = RegisterUserCommand(
            username="manager",
            role=Role.MANAGER,
            name="Alex Smith",
            email="alex@example.com",
            phone_number="0412345678",
            password="secret",
        )

        result = RegisterUserCommandHandler(use_case).execute(command)

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(
            username="manager",
            role=Role.MANAGER,
            name="Alex Smith",
            email="alex@example.com",
            phone_number="0412345678",
            password="secret",
        )

    def test_reset_password_selects_administrative_flow(self) -> None:
        use_case = MagicMock()

        result = ResetUserPasswordCommandHandler(use_case).execute(
            ResetUserPasswordCommand(username="employee", new_password="new")
        )

        self.assertIsNone(result)
        use_case.execute.assert_called_once_with(username="employee", new_password="new")

    def test_create_package_delegates_delivery_and_customer_fields(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        command = CreatePackageCommand(
            start="SYD",
            end="MEL",
            weight=12.5,
            name="Alex Smith",
            email="alex@example.com",
            phone="0412345678",
        )

        result = CreatePackageCommandHandler(use_case).execute(command)

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(
            start="SYD",
            end="MEL",
            weight=12.5,
            name="Alex Smith",
            email="alex@example.com",
            phone="0412345678",
        )

    def test_remove_package_delegates_identifier_and_returns_result(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = RemovePackageCommandHandler(use_case).execute(RemovePackageCommand(package_id=7))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(7)

    def test_assign_packages_converts_immutable_ids_for_existing_use_case(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = AssignPackagesToRouteCommandHandler(use_case).execute(
            AssignPackagesToRouteCommand(route_id=3, package_ids=(4, 5))
        )

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(route_id=3, package_ids=[4, 5])

    def test_assign_truck_delegates_identifiers_and_time(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = AssignTruckToRouteCommandHandler(use_case).execute(
            AssignTruckToRouteCommand(truck_id=2, route_id=3, now=NOW)
        )

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(truck_id=2, route_id=3, now=NOW)

    def test_create_route_delegates_immutable_path_and_departure(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected
        command = CreateRouteCommand(locations=("SYD", "CBR", "MEL"), departure_time=NOW)

        result = CreateRouteCommandHandler(use_case).execute(command)

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(("SYD", "CBR", "MEL"), NOW)

    def test_remove_route_delegates_identifier_and_returns_route(self) -> None:
        use_case = MagicMock()
        expected = object()
        use_case.execute.return_value = expected

        result = RemoveRouteCommandHandler(use_case).execute(RemoveRouteCommand(route_id=8))

        self.assertIs(result, expected)
        use_case.execute.assert_called_once_with(8)

    def test_load_world_delegates_path_and_returns_resolved_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"

        result = LoadWorldCommandHandler(use_case).execute(LoadWorldCommand(path="world.json"))

        self.assertEqual(result, "C:/snapshots/world.json")
        use_case.execute.assert_called_once_with("world.json")

    def test_save_world_delegates_path_and_returns_resolved_path(self) -> None:
        use_case = MagicMock()
        use_case.execute.return_value = "C:/snapshots/world.json"

        result = SaveWorldCommandHandler(use_case).execute(SaveWorldCommand(path="world.json"))

        self.assertEqual(result, "C:/snapshots/world.json")
        use_case.execute.assert_called_once_with("world.json")


if __name__ == "__main__":
    unittest.main()
