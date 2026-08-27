"""Authoritative catalog of concrete commands accepted by the application.

Composition tests compare this catalog with command-bus registrations so a
new command cannot silently remain undispatchable. Runtime dispatch continues
to use each command's typed key; this catalog is not a service locator.
"""

from src.application.commands.auth.change_password import ChangeOwnPasswordCommand
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
from src.application.commands.state.advance_world import AdvanceWorldStateCommand
from src.application.commands.state.load_world import LoadWorldCommand
from src.application.commands.state.save_world import SaveWorldCommand
from src.application.messaging.command import Command

# Keep this tuple synchronized with the explicit bindings in message_buses.
PUBLISHED_COMMAND_TYPES: tuple[type[Command], ...] = (
    LoginCommand,
    LogoutCommand,
    RegisterUserCommand,
    ChangeOwnPasswordCommand,
    ResetUserPasswordCommand,
    CreatePackageCommand,
    RemovePackageCommand,
    CreateRouteCommand,
    RemoveRouteCommand,
    AssignPackagesToRouteCommand,
    AssignTruckToRouteCommand,
    AdvanceWorldStateCommand,
    LoadWorldCommand,
    SaveWorldCommand,
)
