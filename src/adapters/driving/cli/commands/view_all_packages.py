from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires
from src.application.use_cases.packages.view_all_packages import ViewAllPackagesUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class ViewAllPackages(BaseCommand):
    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        view_all_packages_use_case: ViewAllPackagesUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._view_all_packages_use_case = view_all_packages_use_case

    @requires(Permission.PACKAGE_VIEW_ALL)
    def execute(self) -> str:
        packages = self._view_all_packages_use_case.execute()
        return "\n\n".join(package.info() for package in packages) if packages else "No packages."
