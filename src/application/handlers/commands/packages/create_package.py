"""Command handler for package creation."""

from src.application.commands.packages.create_package import CreatePackageCommand
from src.application.use_cases.packages.create_package import CreatePackageUseCase
from src.domain.entities.delivery_package import DeliveryPackage


class CreatePackageCommandHandler:
    """Adapt a package-creation command to the creation workflow."""

    def __init__(self, use_case: CreatePackageUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized package-creation workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: CreatePackageCommand) -> DeliveryPackage:
        """Create a package from the command fields.

        Args:
            command: Delivery and customer data for the new package.

        Returns:
            Newly persisted delivery package.

        Raises:
            Exception: Propagates authorization, validation, domain,
                persistence, and other failures raised by the use case.
        """
        return self._use_case.execute(
            start=command.start,
            end=command.end,
            weight=command.weight,
            name=command.name,
            email=command.email,
            phone=command.phone,
        )
