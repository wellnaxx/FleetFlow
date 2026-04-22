from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.services.authorization_service import requires
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.domain.enums.auth import Permission


class ViewUnassignedPackages(UseCaseCommand[ViewUnassignedPackagesUseCase]):
    """Return a list of packages not attached to any route."""
    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def execute(self) -> str:
        packages = self._use_case.execute()
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(p.info() for p in packages)
