"""Command handler for package removal."""

from src.application.commands.packages.remove_package import RemovePackageCommand
from src.application.results.remove_package_result import RemovePackageResult
from src.application.use_cases.packages.remove_package import RemovePackageUseCase


class RemovePackageCommandHandler:
    """Adapt a package-removal command to the removal workflow."""

    def __init__(self, use_case: RemovePackageUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized package-removal workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: RemovePackageCommand) -> RemovePackageResult:
        """Remove the identified package.

        Args:
            command: Identifier of the package to remove.

        Returns:
            Removal result produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(command.package_id)
