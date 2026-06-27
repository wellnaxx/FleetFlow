"""CLI command for creating delivery packages."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_float, validate_params_count
from src.application.use_cases.packages.create_package import CreatePackageUseCase


class CreatePackage(EventDrainingCommand[CreatePackageUseCase]):
    """Create a package from CLI parameters."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Validate CLI parameters and create a package.

        Returns:
            CLI confirmation text for the created package.

        Raises:
            PermissionError: If the caller lacks package creation permission.
            ValueError: If parameter validation or package creation fails.
        """
        validate_params_count(self._params, 4, 6)

        start = self._params[0]
        end = self._params[1]
        weight = try_parse_float(self._params[2])
        name = self._params[3]
        email = self._params[4] if len(self._params) > 4 else ""
        phone = self._params[5] if len(self._params) > 5 else ""

        package = self._use_case.execute(
            start=start,
            end=end,
            weight=weight,
            name=name,
            email=email,
            phone=phone,
        )

        self._event_collector.drain((package, package.customer))

        return (
            f"Package {package.package_id} was created for customer {name} "
            f"(ID: {package.customer.customer_id}) successfully."
        )
