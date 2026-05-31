from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from src.adapters.driving.http.schemas.customers import CustomerResponse
from src.domain.enums.item_status import ItemStatus


class PackageBase(BaseModel):
    """Base model for a package."""

    start_location: str
    end_location: str
    weight: PositiveFloat = Field(..., description="Package weight in kilograms.")


class PackageCreateRequest(PackageBase):
    """Request model for creating a package."""

    customer_name: str
    customer_email: EmailStr | None = None
    customer_phone_number: str | None = None


class PackageResponse(PackageBase):
    """Response model for a package."""

    package_id: PositiveInt = Field(..., description="Stable package identifier.")
    status: ItemStatus = Field(..., description="Current package status.")
    current_location: str | None = Field(
        None, description="Current package location, or null if not available."
    )
    expected_arrival: datetime | None = Field(
        None,
        description=("Expected arrival time in ISO 8601 format, or null if not available."),
    )
    customer: CustomerResponse
    route_id: PositiveInt | None = Field(
        None, description="Identifier of the assigned delivery route, or null if not assigned."
    )


class PackagePageResponse(BaseModel):
    """Paginated response model for package listings."""

    items: list[PackageResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt


class PackageSuitableRouteResponse(BaseModel):
    """Response model for a route that can carry a package."""

    route_id: PositiveInt = Field(..., description="Identifier of the suitable route.")
    start_location: str = Field(..., description="First location on the suitable route.")
    end_location: str = Field(..., description="Final location on the suitable route.")
    eta: datetime | None = Field(
        None,
        description="Expected arrival at the package destination, or null when unscheduled.",
    )
    capacity_left: NonNegativeFloat | None = Field(
        None,
        description="Remaining truck capacity, or null when no truck is assigned.",
    )
    end_city: str = Field(..., description="Package destination city used for the route match.")
