"""CLI command for creating delivery packages."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import try_parse_float, validate_params_count
from src.application.commands.packages.create_package import CREATE_PACKAGE, CreatePackageCommand


class CreatePackage(CommandBusCommand):
    """Create a package and publish use-case and entity events."""

    mutates_state = True
    autosaves_state = True

    def execute(self) -> str:
        """Validate CLI parameters and create a package.

        Returns:
            CLI confirmation text for the created package.

        Raises:
            PermissionError: If the caller lacks package creation permission.
            ValueError: If parameter validation or package creation fails.
            DatabaseError: If customer or package persistence fails.
            DomainError: If package or customer invariants are violated.
        """
        validate_params_count(self._params, 4, 6)

        start = self._params[0]
        end = self._params[1]
        weight = try_parse_float(self._params[2], "weight")
        name = self._params[3]
        email = self._params[4] if len(self._params) > 4 else ""
        phone = self._params[5] if len(self._params) > 5 else ""

        package = self.command_bus.dispatch(
            key=CREATE_PACKAGE,
            command=CreatePackageCommand(
                start=start,
                end=end,
                weight=weight,
                name=name,
                email=email,
                phone=phone,
            ),
        )

        return (
            f"Package {package.package_id} was created for customer {name} "
            f"(ID: {package.customer.customer_id}) successfully."
        )
