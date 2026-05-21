from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, NonNegativeInt, PositiveFloat, PositiveInt

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
    limit: PositiveInt
    offset: NonNegativeInt
