from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires
from src.application.use_cases.packages.view_unassigned_packages import ViewUnassignedPackagesUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class ViewUnassignedPackages(BaseCommand):
    """Return a list of packages not attached to any route."""

    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        view_unassigned_packages_use_case: ViewUnassignedPackagesUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._view_unassigned_packages_use_case = view_unassigned_packages_use_case

    @requires(Permission.PACKAGE_VIEW_UNASSIGNED)
    def execute(self) -> str:
        packages = self._view_unassigned_packages_use_case.execute()
        if not packages:
            return "No unassigned packages."
        return "\n\n".join(p.info() for p in packages)
