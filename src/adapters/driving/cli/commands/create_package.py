from collections.abc import Iterable

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_float, validate_params_count
from src.application.services.auth_service import AuthService
from src.application.services.authorization import requires
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.core.application_data import ApplicationData
from src.domain.enums.auth import Permission


class CreatePackage(BaseCommand):
    def __init__(
        self,
        params: Iterable[str],
        app_data: ApplicationData,
        auth: AuthService,
        create_package_use_case: CreatePackageUseCase,
    ) -> None:
        super().__init__(params, app_data, auth)
        self._create_package_use_case = create_package_use_case

    mutates_state = True

    @requires(Permission.PACKAGE_CREATE)
    def execute(self) -> str:
        validate_params_count(self._params, 4, 6)

        start = self._params[0]
        end = self._params[1]
        weight = try_parse_float(self._params[2])
        name = self._params[3]
        email = self._params[4] if len(self._params) > 4 else ""
        phone = self._params[5] if len(self._params) > 5 else ""

        pkg = self._create_package_use_case.execute(
            start=start,
            end=end,
            weight=weight,
            name=name,
            email=email,
            phone=phone,
        )

        return (
            f"Package {pkg.package_id} was created for customer {name} "
            f"(ID: {pkg.customer.customer_id}) successfully."
        )
