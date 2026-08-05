"""Command contract for assigning packages to a delivery route."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.results.assign_packages_to_route_result import AssignPackagesToRouteResult


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignPackagesToRouteCommand(Command):
    """Request assignment of one or more packages to a route.

    Attributes:
        route_id: Stable identifier of the target route.
        package_ids: Immutable package identifiers to process. The use case
            retains responsibility for deduplication and per-package results.
    """

    route_id: int
    package_ids: tuple[int, ...]


ASSIGN_PACKAGES_TO_ROUTE: Final[CommandKey[AssignPackagesToRouteCommand, AssignPackagesToRouteResult]] = (
    CommandKey(
        name="assign_packages_to_route",
        command_type=AssignPackagesToRouteCommand,
    )
)
