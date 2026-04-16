import shlex

from adapters.driving.cli.commands.assign_package_to_route import AssignPackageToRoute
from adapters.driving.cli.commands.assign_truck_to_route import AssignTruckToRoute
from adapters.driving.cli.commands.auth_change_password import AuthChangePassword
from adapters.driving.cli.commands.auth_login import AuthLogin
from adapters.driving.cli.commands.auth_logout import AuthLogout
from adapters.driving.cli.commands.auth_register import AuthRegisterUser
from adapters.driving.cli.commands.auth_whoami import AuthWhoAmI
from adapters.driving.cli.commands.base_command.base_command import BaseCommand
from adapters.driving.cli.commands.create_package import CreatePackage
from adapters.driving.cli.commands.create_route import CreateRoute
from adapters.driving.cli.commands.find_suitable_routes_for_package import FindSuitableRoutesForPackage
from adapters.driving.cli.commands.find_suitable_trucks_for_route import FindSuitableTrucksForRoute
from adapters.driving.cli.commands.load_state import LoadState
from adapters.driving.cli.commands.remove_package import RemovePackage
from adapters.driving.cli.commands.remove_route import RemoveRoute
from adapters.driving.cli.commands.save_state import SaveState
from adapters.driving.cli.commands.view_all_customers import ViewAllCustomers
from adapters.driving.cli.commands.view_all_packages import ViewAllPackages
from adapters.driving.cli.commands.view_all_routes import ViewAllRoutes
from adapters.driving.cli.commands.view_all_trucks import ViewAllTrucks
from adapters.driving.cli.commands.view_package import ViewPackage
from adapters.driving.cli.commands.view_route import ViewRoute
from adapters.driving.cli.commands.view_routes_in_progress import ViewRoutesInProgress
from adapters.driving.cli.commands.view_unassigned_packages import ViewUnassignedPackages
from application.services.auth_service import AuthService
from src.core.application_data import ApplicationData

_REGISTRY: dict[str, type[BaseCommand]] = {
    "createroute": CreateRoute,
    "removeroute": RemoveRoute,
    "viewroute": ViewRoute,
    "createpackage": CreatePackage,
    "viewpackage": ViewPackage,
    "removepackage": RemovePackage,
    "findsuitabletrucksforroute": FindSuitableTrucksForRoute,
    "assigntrucktoroute": AssignTruckToRoute,
    "assignpackagetoroute": AssignPackageToRoute,
    "findsuitableroutesforpackage": FindSuitableRoutesForPackage,
    "viewallcustomers": ViewAllCustomers,
    "viewallroutes": ViewAllRoutes,
    "viewallpackages": ViewAllPackages,
    "viewalltrucks": ViewAllTrucks,
    "viewunassignedpackages": ViewUnassignedPackages,
    "viewroutesinprogress": ViewRoutesInProgress,
    "login": AuthLogin,
    "logout": AuthLogout,
    "whoami": AuthWhoAmI,
    "registeruser": AuthRegisterUser,
    "changepassword": AuthChangePassword,
    "save": SaveState,
    "load": LoadState,
}


class CommandFactory:
    """Parses input lines and instantiates command objects bound to app data."""

    def __init__(self, data: ApplicationData, auth: AuthService) -> None:
        self._app_data = data
        self._auth = auth

    def create(self, input_line: str) -> BaseCommand:
        """Create a command from a raw input line.

        Args:
            line: User input (e.g., "createroute SYD MEL 2025-10-12 06:00").
        Returns:
            A command instance with parsed params.
        Raises:
            ValueError: For unknown command names or invalid params.
        """
        tokens = shlex.split(input_line)
        if not tokens:
            raise ValueError("No command given.")
        name, params = tokens[0].lower(), tokens[1:]
        cls = _REGISTRY.get(name)
        if not cls:
            raise ValueError(f"Invalid command name: {name}!")
        return cls(params, self._app_data, self._auth)

    def update_app(self, new_app_data: ApplicationData) -> None:
        """Called by Engine after login/logout to refresh RBAC principal."""
        self._app_data = new_app_data
