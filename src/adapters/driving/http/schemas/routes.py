from datetime import datetime
from typing import Literal, Self

from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from src.application.results.assign_packages_to_route_result import AssignPackagesToRouteResult
from src.application.use_cases.pagination import PageResult
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteResult
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition, RoutePositionKind
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

    @classmethod
    def from_route(cls, route: DeliveryRoute) -> Self:
        """Build an HTTP response from a delivery route entity.

        Args:
            route: Domain route entity returned by a use case.

        Returns:
            Serialized route response.
        """
        return cls(
            route_id=route.route_id,
            locations=[str(location) for location in route.locations],
            departure_time=route.departure_time,
            status=route.status,
            truck_id=route.truck.vehicle_id if route.truck else None,
            total_distance_km=route.total_distance_km,
            eta_final=route.eta_final,
            package_ids=[package.package_id for package in route.packages],
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

    @classmethod
    def from_route_position(
        cls,
        route: DeliveryRoute,
        position: RoutePosition,
    ) -> Self:
        """Build an HTTP response from an active route and computed position.

        Args:
            route: Active route entity.
            position: Computed route position at request time.

        Returns:
            Serialized active route response.

        Raises:
            RuntimeError: If the route position is not an active in-progress kind.
        """
        return cls(
            route=RouteResponse.from_route(route),
            position_kind=_route_position_kind(position),
            current_location=str(position.stop_city) if position.kind == RoutePositionKind.AT_STOP else None,
            in_transit_from=str(position.from_city) if position.kind == RoutePositionKind.IN_TRANSIT else None,
            in_transit_to=str(position.to_city) if position.kind == RoutePositionKind.IN_TRANSIT else None,
        )


class RoutePageResponse(BaseModel):
    """Paginated response model for route listings."""

    items: list[RouteResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt

    @classmethod
    def from_page(cls, page: PageResult[DeliveryRoute]) -> Self:
        """Build a paginated HTTP response from a route page result.

        Args:
            page: Application page result containing route entities.

        Returns:
            Serialized route page response.
        """
        return cls(
            items=[RouteResponse.from_route(route) for route in page.items],
            total=page.total,
            count=page.count,
            limit=page.limit,
            offset=page.offset,
        )


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

    @classmethod
    def from_result(cls, result: AssignPackagesToRouteResult) -> Self:
        """Build an HTTP response from a package-assignment result.

        Args:
            result: Application result containing assignment successes and errors.

        Returns:
            Serialized package-assignment response.
        """
        return cls(
            successes=[
                PackageAssignmentSuccessResponse(
                    package_id=success.package_id,
                    route_id=success.route_id,
                    eta_text=success.eta_text,
                    route=RouteResponse.from_route(success.route),
                )
                for success in result.successes
            ],
            errors=[
                PackageAssignmentErrorResponse(
                    package_id=error.package_id,
                    message=error.message,
                )
                for error in result.errors
            ],
        )


class AssignTruckToRouteRequest(BaseModel):
    """Request model for assigning a truck to a delivery route."""

    truck_id: PositiveInt = Field(..., description="Identifier of the truck to assign to the route.")


class AssignTruckToRouteResponse(BaseModel):
    """Response model for assigning a truck to a delivery route."""

    route_id: PositiveInt = Field(..., description="Identifier of the route to which the truck was assigned.")
    truck_id: PositiveInt = Field(..., description="Identifier of the truck that was assigned to the route.")

    @classmethod
    def from_result(cls, result: AssignTruckToRouteResult) -> Self:
        """Build an HTTP response from a truck-assignment result.

        Args:
            result: Application result containing the assigned route and truck identifiers.

        Returns:
            Serialized truck-assignment response.
        """
        return cls(route_id=result.route_id, truck_id=result.truck_id)


def _route_position_kind(position: RoutePosition) -> RouteInProgressPositionKind:
    """Return the HTTP-supported active route position kind.

    Args:
        position: Computed route position to expose through HTTP.

    Returns:
        Supported active-route position kind.

    Raises:
        RuntimeError: If the position is not an active in-progress position.
    """
    if position.kind == RoutePositionKind.AT_STOP:
        return "AT_STOP"
    if position.kind == RoutePositionKind.IN_TRANSIT:
        return "IN_TRANSIT"
    raise RuntimeError(f"Unsupported in-progress route position kind: {position.kind}")
