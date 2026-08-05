"""Command contract for creating a delivery route."""

from dataclasses import dataclass
from datetime import datetime
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True, kw_only=True)
class CreateRouteCommand(Command):
    """Request creation of a route through an ordered location path.

    Attributes:
        locations: Immutable ordered raw location codes from origin to final
            destination.
        departure_time: Optional business-local departure timestamp. ``None``
            creates a planned, unscheduled route.
    """

    locations: tuple[str, ...]
    departure_time: datetime | None = None


CREATE_ROUTE: Final[CommandKey[CreateRouteCommand, DeliveryRoute]] = CommandKey(
    name="create_route",
    command_type=CreateRouteCommand,
)
