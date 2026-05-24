"""CLI command for listing unassigned packages."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase


class ViewUnassignedPackages(BaseCommand[ViewUnassignedPackagesUseCase]):
    """Return a list of packages not attached to any route."""

    def execute(self) -> str:
        """Return unassigned package listing text.

        Returns:
            CLI listing of unassigned packages, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks unassigned package permission.
        """
        packages = self._use_case.execute().items
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(p.info() for p in packages)
