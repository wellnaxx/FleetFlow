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
from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand, UseCaseCommand
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
from src.composition.container import Container
from src.core.application_data import ApplicationData

_LEGACY_REGISTRY: dict[str, type[BaseCommand]] = {
    "createroute": CreateRoute,
    "removeroute": RemoveRoute,
    "findsuitabletrucksforroute": FindSuitableTrucksForRoute,
    "assigntrucktoroute": AssignTruckToRoute,
    "assignpackagetoroute": AssignPackageToRoute,
    "findsuitableroutesforpackage": FindSuitableRoutesForPackage,
    "viewallroutes": ViewAllRoutes,
    "viewalltrucks": ViewAllTrucks,
    "login": AuthLogin,
    "logout": AuthLogout,
    "whoami": AuthWhoAmI,
    "registeruser": AuthRegisterUser,
    "changepassword": AuthChangePassword,
    "save": SaveState,
    "load": LoadState,
}

type CommandEntry[T] = tuple[type[UseCaseCommand[T]], Callable[[Container], T]]


def bind_command[T](
    command_cls: type[UseCaseCommand[T]],
    getter: Callable[[Container], T],
) -> CommandEntry[T]:
    return command_cls, getter


_CONTAINER_COMMANDS: dict[str, CommandEntry[Any]] = {
    "createpackage": bind_command(CreatePackage, lambda container: container.create_package_use_case),
    "viewpackage": bind_command(ViewPackage, lambda container: container.view_package_use_case),
    "viewallpackages": bind_command(ViewAllPackages, lambda container: container.view_all_packages_use_case),
    "removepackage": bind_command(RemovePackage, lambda container: container.remove_package_use_case),
    "viewunassignedpackages": bind_command(
        ViewUnassignedPackages, lambda container: container.view_unassigned_packages_use_case
    ),
    "viewallcustomers": bind_command(ViewAllCustomers, lambda container: container.view_all_customers_use_case),
    "viewroute": bind_command(ViewRoute, lambda container: container.view_route_use_case),
    "viewallroutes": bind_command(ViewAllRoutes, lambda container: container.view_all_routes_use_case),
    "viewroutesinprogress": bind_command(
        ViewRoutesInProgress, lambda container: container.view_routes_in_progress_use_case
    ),
}


class CommandFactory:
    """Parse raw CLI input and build command objects.

    Uses explicit builders for migrated commands and falls back to the legacy
    command registry for commands that still use the old ApplicationData-based
    path.
    """

    def __init__(self, data: ApplicationData, auth: AuthService, container: Container) -> None:
        self._app_data = data
        self._auth = auth
        self._container = container

    def create(self, input_line: str) -> BaseCommand:
        """Create a command from a raw input line.

        Args:
            input_line: User input (e.g., "createroute SYD MEL 2025-10-12 06:00").
        Returns:
            A command instance with parsed params.
        Raises:
            ValueError: For unknown command names or invalid params.
        """
        tokens = shlex.split(input_line)
        if not tokens:
            raise ValueError("No command given.")
        name, params = tokens[0].lower(), tokens[1:]

        if entry := _CONTAINER_COMMANDS.get(name):
            cls, get_use_case = entry
            return cls(params, self._app_data, self._auth, get_use_case(self._container))

        if cls := _LEGACY_REGISTRY.get(name):
            return cls(params, self._app_data, self._auth)

        raise ValueError(f"Invalid command name: {name}!")

    def update_app(self, new_app_data: ApplicationData) -> None:
        """Called by Engine after login/logout to refresh RBAC principal."""
        self._app_data = new_app_data
