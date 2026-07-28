from datetime import datetime
from typing import Self

from pydantic import BaseModel, EmailStr, Field, NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from src.adapters.driving.http.schemas.customers import CustomerResponse
from src.application.results.find_suitable_packages_for_route_result import SuitableRouteForPackage
from src.application.use_cases.pagination import PageResult
from src.domain.entities.delivery_package import DeliveryPackage
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

    @classmethod
    def from_package(cls, package: DeliveryPackage) -> Self:
        """Build an HTTP response from a package entity.

        Args:
            package: Domain package entity returned by a use case.

        Returns:
            Serialized package response.
        """
        return cls(
            start_location=str(package.start_location),
            end_location=str(package.end_location),
            weight=package.weight,
            package_id=package.package_id,
            status=package.status,
            current_location=str(package.current_location) if package.current_location else None,
            expected_arrival=package.expected_arrival,
            customer=CustomerResponse.from_customer(package.customer),
            route_id=package.route_id,
        )


class PackagePageResponse(BaseModel):
    """Paginated response model for package listings."""

    items: list[PackageResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt

    @classmethod
    def from_page(cls, page: PageResult[DeliveryPackage]) -> Self:
        """Build a paginated HTTP response from a package page result.

        Args:
            page: Application page result containing package entities.

        Returns:
            Serialized package page response.
        """
        return cls(
            items=[PackageResponse.from_package(package) for package in page.items],
            total=page.total,
            count=page.count,
            limit=page.limit,
            offset=page.offset,
        )


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

    @classmethod
    def from_match(cls, match: SuitableRouteForPackage) -> Self:
        """Build an HTTP response from a suitable-route match.

        Args:
            match: Application result describing one route that can carry a package.

        Returns:
            Serialized suitable-route response.
        """
        return cls(
            route_id=match.route_id,
            start_location=str(match.start_location),
            end_location=str(match.end_location),
            eta=match.eta,
            capacity_left=match.capacity_left,
            end_city=str(match.end_city),
        )
