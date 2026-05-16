"""CLI command for listing packages."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase


class ViewAllPackages(BaseCommand[ViewAllPackagesUseCase]):
    """Render all packages."""

    def execute(self) -> str:
        """Return package listing text.

        Returns:
            CLI listing of packages, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks package listing permission.
        """
        packages = self._use_case.execute()
        return "\n\n".join(package.info() for package in packages) if packages else "No packages."
