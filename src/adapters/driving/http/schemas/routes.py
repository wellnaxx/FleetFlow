from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from src.domain.enums.route_status import RouteStatus

type RouteInProgressPositionKind = Literal["AT_STOP", "IN_TRANSIT"]


class RouteCreateRequest(BaseModel):
    """Request model for creating a delivery route."""

    locations: list[str] = Field(
        ...,
        min_length=2,
        description="Ordered list of location codes for the route.",
    )
    departure_time: datetime | None = Field(None, description="Scheduled departure time in ISO 8601 format.")


class RouteResponse(BaseModel):
    """Response model for a delivery route."""

    route_id: PositiveInt = Field(..., description="Stable route identifier.")
    locations: list[str] = Field(..., description="Ordered list of location codes for the route.")
    departure_time: datetime | None = Field(None, description="Scheduled departure time in ISO 8601 format.")
    status: RouteStatus = Field(..., description="Current route status.")
    truck_id: PositiveInt | None = Field(
        None, description="Identifier of the assigned truck, or null if not assigned."
    )
    total_distance_km: PositiveInt = Field(..., description="Total distance of the route in kilometers.")
    eta_final: datetime | None = Field(
        None, description="Estimated time of arrival at the final destination in ISO 8601 format."
    )
    package_ids: list[PositiveInt] = Field(
        ..., description="List of package identifiers assigned to this route."
    )


class RouteInProgressResponse(BaseModel):
    """Response model for a delivery route in-progress."""

    route: RouteResponse
    position_kind: RouteInProgressPositionKind = Field(
        ...,
        description="Computed active-route position kind. Allowed values are AT_STOP or IN_TRANSIT.",
        examples=["AT_STOP"],
    )
    current_location: str | None = None
    in_transit_from: str | None = None
    in_transit_to: str | None = None


class RoutePageResponse(BaseModel):
    """Paginated response model for route listings."""

    items: list[RouteResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt


class AssignPackagesToRouteRequest(BaseModel):
    """Request model for assigning packages to a delivery route."""

    package_ids: list[PositiveInt] = Field(
        ...,
        min_length=1,
        description="List of package identifiers to assign.",
    )


class PackageAssignmentSuccessResponse(BaseModel):
    """Response model for successful package assignment to a route."""

    package_id: PositiveInt = Field(
        ..., description="Identifier of the package that was successfully assigned."
    )
    route_id: PositiveInt = Field(..., description="Identifier of the route to which the package was assigned.")
    eta_text: str = Field(
        ..., description="Human-readable estimated time of arrival for the package at its destination."
    )
    route: RouteResponse = Field(..., description="Updated route after the package assignment.")


class PackageAssignmentErrorResponse(BaseModel):
    """Response model for failed package assignment to a route."""

    package_id: PositiveInt = Field(..., description="Identifier of the package that failed to be assigned.")
    message: str = Field(..., description="Error message describing the reason for the assignment failure.")


class AssignPackagesToRouteResponse(BaseModel):
    """Response model for batch assignment of packages to a route, including successes and errors."""

    successes: list[PackageAssignmentSuccessResponse] = Field(
        ..., description="List of successful package assignments."
    )
    errors: list[PackageAssignmentErrorResponse] = Field(..., description="List of package assignment errors.")


class AssignTruckToRouteRequest(BaseModel):
    """Request model for assigning a truck to a delivery route."""

    truck_id: PositiveInt = Field(..., description="Identifier of the truck to assign to the route.")


class AssignTruckToRouteResponse(BaseModel):
    """Response model for assigning a truck to a delivery route."""

    route_id: PositiveInt = Field(..., description="Identifier of the route to which the truck was assigned.")
    truck_id: PositiveInt = Field(..., description="Identifier of the truck that was assigned to the route.")
