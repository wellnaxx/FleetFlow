"""Factory for parsing CLI input into command instances."""

import shlex
from collections.abc import Callable
from typing import Any

from src.adapters.driving.cli.commands.assign_packages_to_route import AssignPackagesToRoute
from src.adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute
from src.adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from src.adapters.driving.cli.commands.auth_login import AuthLogin
from src.adapters.driving.cli.commands.auth_logout import AuthLogout
from src.adapters.driving.cli.commands.auth_register import AuthRegisterUser
from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.create_package import CreatePackage
from src.adapters.driving.cli.commands.create_route import CreateRoute
from src.adapters.driving.cli.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage
from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute
from src.adapters.driving.cli.commands.load_state import LoadState
from src.adapters.driving.cli.commands.remove_package import RemovePackage
from src.adapters.driving.cli.commands.remove_route import RemoveRoute
from src.adapters.driving.cli.commands.save_state import SaveState
from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from src.adapters.driving.cli.commands.view_package import ViewPackage
from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from src.composition.container import Container

type CommandEntry[T] = tuple[type[BaseCommand[T]], Callable[[Container], T]]


def bind_command[T](
    command_cls: type[BaseCommand[T]],
    getter: Callable[[Container], T],
) -> CommandEntry[T]:
    """Bind a command class to the container lookup for its use case.

    Args:
        command_cls: CLI command class to instantiate.
        getter: Function that retrieves the matching use case from the container.

    Returns:
        A registry entry consumed by `CommandFactory`.
    """
    return command_cls, getter


_CONTAINER_COMMANDS: dict[str, CommandEntry[Any]] = {
    "save": bind_command(SaveState, lambda container: container.state_cases.save),
    "load": bind_command(LoadState, lambda container: container.state_cases.load),
    "login": bind_command(AuthLogin, lambda container: container.auth_cases.login),
    "logout": bind_command(AuthLogout, lambda container: container.auth_cases.logout),
    "whoami": bind_command(AuthWhoAmI, lambda container: container.auth_cases.who_am_i),
    "registeruser": bind_command(AuthRegisterUser, lambda container: container.auth_cases.register_user),
    "changepassword": bind_command(AuthChangePassword, lambda container: container.auth_cases.change_password),
    "createpackage": bind_command(CreatePackage, lambda container: container.package_cases.create),
    "viewpackage": bind_command(ViewPackage, lambda container: container.package_cases.view),
    "viewallpackages": bind_command(ViewAllPackages, lambda container: container.package_cases.view_all),
    "removepackage": bind_command(RemovePackage, lambda container: container.package_cases.remove),
    "viewunassignedpackages": bind_command(
        ViewUnassignedPackages, lambda container: container.package_cases.view_unassigned
    ),
    "viewallcustomers": bind_command(ViewAllCustomers, lambda container: container.customer_cases.view_all),
    "createroute": bind_command(CreateRoute, lambda container: container.route_cases.create),
    "viewroute": bind_command(ViewRoute, lambda container: container.route_cases.view),
    "viewallroutes": bind_command(ViewAllRoutes, lambda container: container.route_cases.view_all),
    "viewroutesinprogress": bind_command(
        ViewRoutesInProgress, lambda container: container.route_cases.view_in_progress
    ),
    "removeroute": bind_command(RemoveRoute, lambda container: container.route_cases.remove),
    "assigntrucktoroute": bind_command(
        AssignTruckToRoute, lambda container: container.route_cases.assign_truck
    ),
    "findsuitabletrucksforroute": bind_command(
        FindSuitableTrucksForRoute, lambda container: container.route_cases.find_suitable_trucks
    ),
    "findsuitableroutesforpackage": bind_command(
        FindSuitableRoutesForPackage, lambda container: container.route_cases.find_suitable_routes
    ),
    "assignpackagestoroute": bind_command(
        AssignPackagesToRoute, lambda container: container.route_cases.assign_packages
    ),
    "viewalltrucks": bind_command(ViewAllTrucks, lambda container: container.truck_cases.view_all),
}


class CommandFactory:
    """Parse CLI input and create fully wired command objects."""

    def __init__(self, container: Container) -> None:
        """Initialize the factory with the application container.

        Args:
            container: Dependency container holding command use cases.
        """
        self._container = container

    def create(self, input_line: str) -> BaseCommand[Any]:
        """Create a command instance from raw CLI input.

        Args:
            input_line: Raw command line entered by the user.

        Returns:
            A concrete command instance bound to its use case.

        Raises:
            ValueError: If no command is provided or the command name is unknown.
        """
        tokens = shlex.split(input_line)
        if not tokens:
            raise ValueError("No command given.")
        name, params = tokens[0].lower(), tokens[1:]

        entry = _CONTAINER_COMMANDS.get(name)
        if entry is None:
            raise ValueError(f"Invalid command name: {name}!")

        cls, get_use_case = entry
        return cls(params, get_use_case(self._container))
