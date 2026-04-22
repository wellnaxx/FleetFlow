from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_int, validate_params_exact
from src.application.services.authorization_service import requires_all
from src.application.use_cases.packages.remove_package import RemovePackageUseCase
from src.domain.enums.auth import Permission


class RemovePackage(UseCaseCommand[RemovePackageUseCase]):
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

    @requires_all(Permission.PACKAGE_REMOVE, Permission.PACKAGE_VIEW)
    def execute(self) -> str:
        validate_params_exact(self._params, 1)
        package_id = try_parse_int(self._params[0])
        self._use_case.execute(package_id)
        return f"Package {package_id} removed."
