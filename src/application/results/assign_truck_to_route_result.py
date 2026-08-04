"""Result contract for a successful truck-to-route assignment."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True, slots=True)
class AssignTruckToRouteResult:
    """Identify the assigned truck and expose the updated route aggregate.

    Attributes:
        route_id: Stable identifier of the updated route.
        truck_id: Stable identifier of the assigned truck.
        route: Updated route carrying assignment events for later publication.
    """

    route_id: int
    truck_id: int
    route: DeliveryRoute
