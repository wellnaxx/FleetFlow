"""CLI command for removing delivery packages."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.commands.packages.remove_package import REMOVE_PACKAGE, RemovePackageCommand


class RemovePackage(CommandBusCommand):
    """Remove a delivery package by id.

    Usage:
        removepackage <package_id>

    Examples:
        removepackage 42
    """

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Remove the requested package.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller lacks required package permissions.
            ValueError: If the package id cannot be parsed.
            NotFoundError: If the package does not exist.
            DomainConflictError: If package ownership or route assignment is
                inconsistent.
            DatabaseError: If package removal cannot be persisted.
        """
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0], "package_id")
        self.command_bus.dispatch(
            key=REMOVE_PACKAGE,
            command=RemovePackageCommand(package_id=package_id),
        )
        return f"Package {package_id} removed."
