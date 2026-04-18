from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires
from src.application.use_cases.packages.view_package import ViewPackageUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class ViewPackage(BaseCommand):
    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        view_package_use_case: ViewPackageUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._view_package_use_case = view_package_use_case

    @requires(Permission.PACKAGE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        package = self._view_package_use_case.execute(package_id)
        return package.info()
