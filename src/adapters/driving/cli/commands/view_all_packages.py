"""CLI command for listing packages."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.rendering.package_info_renderer import render_package_info
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase


class ViewAllPackages(EventDrainingCommand[ViewAllPackagesUseCase]):
    """Render all packages."""

    def execute(self) -> str:
        """Return package listing text.

        Returns:
            CLI listing of packages, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks package listing permission.
        """
        packages = self._run_and_drain(self._use_case, self._use_case.execute).items
        return "\n\n".join(render_package_info(package) for package in packages) if packages else "No packages."
