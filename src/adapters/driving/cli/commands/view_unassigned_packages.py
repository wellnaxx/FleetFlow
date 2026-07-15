"""CLI command for listing unassigned packages."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase


class ViewUnassignedPackages(EventDrainingCommand[ViewUnassignedPackagesUseCase]):
    """Return a list of packages not attached to any route."""

    def execute(self) -> str:
        """Return unassigned package listing text.

        Returns:
            CLI listing of unassigned packages, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks unassigned package permission.
        """
        packages = self._run_and_drain(self._use_case, self._use_case.execute).items
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(render_package_info(package) for package in packages)
