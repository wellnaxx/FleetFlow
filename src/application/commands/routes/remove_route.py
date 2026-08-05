"""Command contract for removing a delivery route."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.command import Command, CommandKey
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True, kw_only=True)
class RemoveRouteCommand(Command):
    """Request removal of one route and coordinated assignment cleanup.

    Attributes:
        route_id: Stable identifier of the route to remove.
    """

    route_id: int


REMOVE_ROUTE: Final[CommandKey[RemoveRouteCommand, DeliveryRoute]] = CommandKey(
    name="remove_route",
    command_type=RemoveRouteCommand,
)
