"""Command contract for assigning a truck to a delivery route."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.application.results.assign_truck_to_route_result import AssignTruckToRouteResult
from src.shared.validation import require_naive_datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class AssignTruckToRouteCommand(Command):
    """Request assignment of a truck to a route at a deterministic time.

    Attributes:
        truck_id: Stable identifier of the truck to assign.
        route_id: Stable identifier of the target route.
        now: Business-local time used for suitability checks and scheduling an
            otherwise unscheduled route.
    """

    truck_id: int
    route_id: int
    now: datetime

    def __post_init__(self) -> None:
        """Require a timezone-naive app-local assignment timestamp."""
        require_naive_datetime(self.now, "now")


ASSIGN_TRUCK_TO_ROUTE: Final[CommandKey[AssignTruckToRouteCommand, AssignTruckToRouteResult]] = CommandKey(
    name="assign_truck_to_route",
    command_type=AssignTruckToRouteCommand,
)
