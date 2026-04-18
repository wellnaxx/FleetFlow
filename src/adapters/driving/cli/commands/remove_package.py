from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires_all
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class RemovePackage(BaseCommand):
    """
    Remove a delivery package by ID.

    Usage:
      removepackage <package_id>
      removepackage <package_id>

    Examples:
      removepackage 42
      removepackage 42
    """

    mutates_state = True

    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        remove_package_use_case: RemovePackageUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._remove_package_use_case = remove_package_use_case

    @requires_all(Permission.PACKAGE_REMOVE, Permission.PACKAGE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        self._remove_package_use_case.execute(package_id)
        return f"Package {package_id} removed."
