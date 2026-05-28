from datetime import datetime
from typing import Self

from pydantic import BaseModel, Field, PositiveInt, model_validator

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
