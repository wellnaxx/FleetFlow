"""CLI command for removing delivery packages."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.packages.remove_package import RemovePackageUseCase


class RemovePackage(EventDrainingCommand[RemovePackageUseCase]):
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
            ValueError: If the package id is invalid or the package is missing.
        """
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0], "package_id")
        result = self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(package_id),
        )

        self._event_collector.drain(
            (result.package, result.customer)
            if result.route is None
            else (result.package, result.customer, result.route)
        )
        return f"Package {package_id} removed."
