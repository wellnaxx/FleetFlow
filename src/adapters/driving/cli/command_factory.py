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
from src.adapters.driving.cli.commands.auth_reset_password import AuthResetPassword
from src.adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.create_package import CreatePackage
from src.adapters.driving.cli.commands.create_route import CreateRoute
from src.adapters.driving.cli.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage
from src.adapters.driving.cli.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute
from src.adapters.driving.cli.commands.get_fleet_overview import GetFleetOverview
from src.adapters.driving.cli.commands.load_state import LoadState
from src.adapters.driving.cli.commands.remove_package import RemovePackage
from src.adapters.driving.cli.commands.remove_route import RemoveRoute
from src.adapters.driving.cli.commands.save_state import SaveState
from src.adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from src.adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from src.adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from src.adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from src.adapters.driving.cli.commands.view_audits import ViewAuditLogs
from src.adapters.driving.cli.commands.view_package import ViewPackage
from src.adapters.driving.cli.commands.view_route import ViewRoute
from src.adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from src.adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from src.composition.container import Container

type CommandParams = tuple[str, ...]
type CommandBuilder = Callable[[Container, CommandParams], BaseCommand[Any]]

_CONTAINER_COMMANDS: dict[str, CommandBuilder] = {
    "login": lambda container, params: AuthLogin(params, container.command_bus),
    "logout": lambda container, params: AuthLogout(params, container.command_bus),
    "whoami": lambda container, params: AuthWhoAmI(params, container.query_bus),
    "registeruser": lambda container, params: AuthRegisterUser(params, container.command_bus),
    "changepassword": lambda container, params: AuthChangePassword(params, container.command_bus),
    "resetpassword": lambda container, params: AuthResetPassword(params, container.command_bus),
    "save": lambda container, params: SaveState(params, container.state_cases.save, container.event_collector),
    "load": lambda container, params: LoadState(params, container.state_cases.load, container.event_collector),
    "createpackage": lambda container, params: CreatePackage(params, container.command_bus),
    "viewpackage": lambda container, params: ViewPackage(params, container.query_bus),
    "viewallpackages": lambda container, params: ViewAllPackages(params, container.query_bus),
    "removepackage": lambda container, params: RemovePackage(params, container.command_bus),
    "viewunassignedpackages": lambda container, params: ViewUnassignedPackages(params, container.query_bus),
    "viewallcustomers": lambda container, params: ViewAllCustomers(params, container.query_bus),
    "createroute": lambda container, params: CreateRoute(params, container.command_bus),
    "viewroute": lambda container, params: ViewRoute(
        params, container.route_cases.view, container.event_collector
    ),
    "viewallroutes": lambda container, params: ViewAllRoutes(
        params, container.route_cases.view_all, container.event_collector
    ),
    "viewroutesinprogress": lambda container, params: ViewRoutesInProgress(
        params, container.route_cases.view_in_progress, container.event_collector
    ),
    "removeroute": lambda container, params: RemoveRoute(
        params, container.route_cases.remove, container.event_collector
    ),
    "assigntrucktoroute": lambda container, params: AssignTruckToRoute(params, container.command_bus),
    "assignpackagestoroute": lambda container, params: AssignPackagesToRoute(params, container.command_bus),
    "findsuitabletrucksforroute": lambda container, params: FindSuitableTrucksForRoute(
        params, container.route_cases.find_suitable_trucks, container.event_collector
    ),
    "findsuitableroutesforpackage": lambda container, params: FindSuitableRoutesForPackage(
        params, container.route_cases.find_suitable_routes, container.event_collector
    ),
    "viewalltrucks": lambda container, params: ViewAllTrucks(
        params, container.truck_cases.view_all, container.event_collector
    ),
    "viewauditlogs": lambda container, params: ViewAuditLogs(params, container.query_bus),
    "getfleetoverview": lambda container, params: GetFleetOverview(params, container.query_bus),
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

        builder = _CONTAINER_COMMANDS.get(name)
        if builder is None:
            raise ValueError(f"Invalid command name: {name}!")

        return builder(self._container, tuple(params))
