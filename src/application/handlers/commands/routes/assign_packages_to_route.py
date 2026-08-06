"""Command handler for assigning packages to a route."""

from src.application.commands.routes.assign_packages_to_route import AssignPackagesToRouteCommand
from src.application.results.assign_packages_to_route_result import AssignPackagesToRouteResult
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase


class AssignPackagesToRouteCommandHandler:
    """Adapt an immutable assignment command to the existing route workflow."""

    def __init__(self, use_case: AssignPackagesToRouteUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized package-assignment workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: AssignPackagesToRouteCommand) -> AssignPackagesToRouteResult:
        """Assign the requested packages to the target route.

        Args:
            command: Route identifier and immutable package identifiers.

        Returns:
            Per-package assignment result produced by the use case.

        Raises:
            Exception: Propagates authorization, lookup, domain, persistence,
                and other failures raised by the use case.
        """
        return self._use_case.execute(
            route_id=command.route_id,
            package_ids=list(command.package_ids),
        )
