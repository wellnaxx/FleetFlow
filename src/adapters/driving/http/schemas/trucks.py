from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, PositiveInt, model_validator

from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus


class TruckResponse(BaseModel):
    """Response schema for truck resources returned by the API."""

    vehicle_id: PositiveInt = Field(..., description="Stable truck identifier.")
    name: str = Field(..., description="Human-readable truck name or model.")
    capacity: PositiveInt = Field(..., description="Maximum load capacity of the truck in kilograms.")
    max_range: PositiveInt = Field(
        ..., description="Maximum range of the truck on a full charge in kilometers."
    )
    status: TruckStatus = Field(..., description="Current truck status.")
    current_location: str | None = Field(
        None, description="Current location of the truck, or null if not available."
    )
    route_id: PositiveInt | None = Field(
        None, description="Identifier of the assigned delivery route, or null if not assigned."
    )
    busy_from: datetime | None = Field(
        None,
        description="Start time of the truck's current assignment in ISO 8601 format, or null if not busy.",
    )
    busy_until: datetime | None = Field(
        None, description="End time of the truck's current assignment in ISO 8601 format, or null if not busy."
    )
    in_transit_to: str | None = Field(
        None, description="Destination location of the truck if it is currently in transit."
    )

    @model_validator(mode="after")
    def validate_busy_window(self) -> Self:
        """Reject truck assignment windows whose end precedes the start."""
        if self.busy_from is not None and self.busy_until is not None and self.busy_from > self.busy_until:
            raise ValueError("busy_from must be before or equal to busy_until.")
        return self

    @classmethod
    def from_truck(cls, truck: Truck) -> Self:
        """Build an HTTP response from a truck entity.

        Args:
            truck: Domain truck entity returned by a use case.

        Returns:
            Serialized truck response.
        """
        return cls(
            vehicle_id=truck.vehicle_id,
            name=str(truck.name),
            capacity=truck.capacity,
            max_range=truck.max_range,
            status=truck.status,
            current_location=str(truck.current_location) if truck.current_location is not None else None,
            route_id=truck.route.route_id if truck.route is not None else None,
            busy_from=truck.busy_from,
            busy_until=truck.busy_until,
            in_transit_to=str(truck.in_transit_to) if truck.in_transit_to is not None else None,
        )
