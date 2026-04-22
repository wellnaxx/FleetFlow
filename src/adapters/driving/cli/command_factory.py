import shlex
from collections.abc import Callable
from typing import Any

from src.adapters.driving.cli.commands.assign_package_to_route import AssignPackageToRoute
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
from src.application.services.auth_service import AuthService
from src.application.services.authorization_service import AuthorizationService
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
    "save": bind_command(SaveState, lambda container: container.save_world_state_use_case),
    "load": bind_command(LoadState, lambda container: container.load_world_state_use_case),
    "login": bind_command(AuthLogin, lambda container: container.login_use_case),
    "logout": bind_command(AuthLogout, lambda container: container.logout_use_case),
    "whoami": bind_command(AuthWhoAmI, lambda container: container.who_am_i_use_case),
    "registeruser": bind_command(AuthRegisterUser, lambda container: container.register_user_use_case),
    "changepassword": bind_command(AuthChangePassword, lambda container: container.change_password_use_case),
    "createpackage": bind_command(CreatePackage, lambda container: container.create_package_use_case),
    "viewpackage": bind_command(ViewPackage, lambda container: container.view_package_use_case),
    "viewallpackages": bind_command(ViewAllPackages, lambda container: container.view_all_packages_use_case),
    "removepackage": bind_command(RemovePackage, lambda container: container.remove_package_use_case),
    "viewunassignedpackages": bind_command(
        ViewUnassignedPackages, lambda container: container.view_unassigned_packages_use_case
    ),
    "viewallcustomers": bind_command(ViewAllCustomers, lambda container: container.view_all_customers_use_case),
    "createroute": bind_command(CreateRoute, lambda container: container.create_route_use_case),
    "viewroute": bind_command(ViewRoute, lambda container: container.view_route_use_case),
    "viewallroutes": bind_command(ViewAllRoutes, lambda container: container.view_all_routes_use_case),
    "viewroutesinprogress": bind_command(
        ViewRoutesInProgress, lambda container: container.view_routes_in_progress_use_case
    ),
    "removeroute": bind_command(RemoveRoute, lambda container: container.remove_route_use_case),
    "assigntrucktoroute": bind_command(
        AssignTruckToRoute, lambda container: container.assign_truck_to_route_use_case
    ),
    "findsuitabletrucksforroute": bind_command(
        FindSuitableTrucksForRoute, lambda container: container.find_suitable_trucks_for_route_use_case
    ),
    "findsuitableroutesforpackage": bind_command(
        FindSuitableRoutesForPackage, lambda container: container.find_suitable_routes_for_package_use_case
    ),
    "assignpackagestoroute": bind_command(
        AssignPackageToRoute, lambda container: container.assign_packages_to_route_use_case
    ),
    "viewalltrucks": bind_command(ViewAllTrucks, lambda container: container.view_all_trucks_use_case),
}


class CommandFactory:
    """Parse CLI input and create fully wired command objects."""

    def __init__(self, auth: AuthService, authz: AuthorizationService, container: Container) -> None:
        """Initialize the factory with shared command dependencies.

        Args:
            auth: Authentication service exposed to commands.
            authz: Authorization service exposed to commands.
            container: Dependency container holding command use cases.
        """
        self._auth = auth
        self._authz = authz
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
        return cls(params, self._auth, self._authz, get_use_case(self._container))
