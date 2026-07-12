"""CLI command for viewing a package."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.use_cases.packages.view_package import ViewPackageUseCase


class ViewPackage(EventDrainingCommand[ViewPackageUseCase]):
    """Render one package by id."""

    def execute(self) -> str:
        """Fetch a package and return display text.

        Returns:
            Multi-line package summary.

        Raises:
            PermissionError: If the caller lacks package view permission.
            ValueError: If the parameter count or id is invalid.
        """
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0], "package_id")
        package = self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(package_id),
        )
        return package.info()
