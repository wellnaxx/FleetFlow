from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.use_cases import (
    get_assign_packages_to_route_use_case,
    get_assign_truck_to_route_use_case,
    get_create_route_use_case,
    get_find_suitable_trucks_for_route_use_case,
    get_remove_route_use_case,
    get_view_all_routes_use_case,
    get_view_route_use_case,
    get_view_routes_in_progress_use_case,
)
from src.adapters.driving.http.routers.shared import truck_response
from src.adapters.driving.http.schemas.routes import (
    AssignPackagesToRouteRequest,
    AssignPackagesToRouteResponse,
    AssignTruckToRouteRequest,
    AssignTruckToRouteResponse,
    PackageAssignmentErrorResponse,
    PackageAssignmentSuccessResponse,
    RouteCreateRequest,
    RouteInProgressPositionKind,
    RouteInProgressResponse,
    RoutePageResponse,
    RouteResponse,
)
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.application.exceptions.application_errors import ConflictError, NotFoundError
from src.application.results.assign_packages_to_route_result import AssignPackagesToRouteResult
from src.application.use_cases.pagination import PageQuery
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition

routes_router = APIRouter(prefix="/routes", tags=["routes"])


def _route_response(route: DeliveryRoute) -> RouteResponse:
    """Convert a route entity to an HTTP response model.

    Args:
        route: Route entity to convert.

    Returns:
        Response model representing the route.
    """
    return RouteResponse(
        route_id=route.route_id,
        locations=[str(location) for location in route.locations],
        departure_time=route.departure_time,
        status=route.status,
        truck_id=route.truck.vehicle_id if route.truck else None,
        total_distance_km=route.total_distance_km,
        eta_final=route.eta_final,
        package_ids=[package.package_id for package in route.packages],
    )


def _route_in_progress_response(route: DeliveryRoute, position: RoutePosition) -> RouteInProgressResponse:
    """Convert an active route and computed position into an HTTP response.

    Args:
        route: Active route entity.
        position: Computed route position at the request time.

    Returns:
        Response model containing route details and active position fields.
    """
    return RouteInProgressResponse(
        route=_route_response(route),
        position_kind=_route_position_kind(position),
        current_location=str(position.stop_city) if position.kind == "AT_STOP" else None,
        in_transit_from=str(position.from_city) if position.kind == "IN_TRANSIT" else None,
        in_transit_to=str(position.to_city) if position.kind == "IN_TRANSIT" else None,
    )


def _route_position_kind(position: RoutePosition) -> RouteInProgressPositionKind:
    """Return the HTTP-supported active route position kind.

    Args:
        position: Computed route position to expose through HTTP.

    Returns:
        Supported active-route position kind.

    Raises:
        ValueError: If the position is not an active in-progress position.
    """
    if position.kind == "AT_STOP":
        return "AT_STOP"
    if position.kind == "IN_TRANSIT":
        return "IN_TRANSIT"
    raise ValueError(f"Unsupported in-progress route position kind: {position.kind}")


def _assign_packages_response(
    result: AssignPackagesToRouteResult,
) -> AssignPackagesToRouteResponse:
    """Convert a package-assignment use-case result into an HTTP response.

    Args:
        result: Application result containing assignment successes and errors.

    Returns:
        HTTP response model with nested success and error details.
    """
    return AssignPackagesToRouteResponse(
        successes=[
            PackageAssignmentSuccessResponse(
                package_id=success.package_id,
                route_id=success.route_id,
                eta_text=success.eta_text,
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


@routes_router.post("/", status_code=status.HTTP_201_CREATED)
def create_route(
    request: RouteCreateRequest,
    use_case: Annotated[CreateRouteUseCase, Depends(get_create_route_use_case)],
) -> RouteResponse:
    """Create a new delivery route.

    Args:
        request: The request body containing route creation details.
        use_case: Use case for creating a route, injected by FastAPI.

    Returns:
        The created route details.

    Raises:
        HTTPException 400: If route creation input is invalid.
        HTTPException 403: If the caller lacks permission to create routes.
    """
    try:
        route = use_case.execute(
            locations=request.locations,
            departure_time=request.departure_time,
        )
        return _route_response(route)

    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@routes_router.get("/", status_code=status.HTTP_200_OK)
def list_routes(
    use_case: Annotated[ViewAllRoutesUseCase, Depends(get_view_all_routes_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> RoutePageResponse:
    """List delivery routes with pagination.

    Args:
        use_case: Use case for listing routes, injected by FastAPI.
        limit: Maximum number of routes to return.
        offset: Number of routes to skip.
        include_total: Whether to include the total route count.

    Returns:
        A paginated response containing route details.

    Raises:
        HTTPException 403: If the caller lacks permission to view routes.
    """
    try:
        result = use_case.execute(PageQuery(limit=limit, offset=offset, include_total=include_total))
        items = [_route_response(route) for route in result.items]
        return RoutePageResponse(
            items=items,
            total=result.total,
            count=result.count,
            limit=result.limit or limit,
            offset=result.offset,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@routes_router.get("/in-progress", status_code=status.HTTP_200_OK)
def list_in_progress_routes(
    use_case: Annotated[ViewRoutesInProgressUseCase, Depends(get_view_routes_in_progress_use_case)],
) -> list[RouteInProgressResponse]:
    """List routes that are currently at a stop or in transit.

    Args:
        use_case: Use case for listing active routes, injected by FastAPI.

    Returns:
        Active route details with computed position information.

    Raises:
        HTTPException 403: If the caller lacks permission to view in-progress routes.
    """
    try:
        now = datetime.now()
        active_routes = use_case.execute(now=now)
        return [_route_in_progress_response(route, position) for route, position in active_routes]
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


@routes_router.get("/{route_id}", status_code=status.HTTP_200_OK)
def get_route(
    route_id: int, use_case: Annotated[ViewRouteUseCase, Depends(get_view_route_use_case)]
) -> RouteResponse:
    """Return one delivery route by id.

    Args:
        route_id: Identifier of the route to retrieve.
        use_case: Use case for retrieving one route, injected by FastAPI.

    Returns:
        Route details for the requested route.

    Raises:
        HTTPException 403: If the caller lacks permission to view the route.
        HTTPException 404: If the route does not exist.
    """
    try:
        route = use_case.execute(route_id=route_id)
        return _route_response(route)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@routes_router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int, use_case: Annotated[RemoveRouteUseCase, Depends(get_remove_route_use_case)]
) -> None:
    """Remove one delivery route by id.

    Args:
        route_id: Identifier of the route to remove.
        use_case: Use case for removing one route, injected by FastAPI.

    Returns:
        None.

    Raises:
        HTTPException 403: If the caller lacks permission to remove routes.
        HTTPException 404: If the route does not exist.
    """
    try:
        use_case.execute(route_id=route_id)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e


@routes_router.patch("/{route_id}/packages", status_code=status.HTTP_200_OK)
def assign_packages_to_route(
    route_id: int,
    request: AssignPackagesToRouteRequest,
    use_case: Annotated[AssignPackagesToRouteUseCase, Depends(get_assign_packages_to_route_use_case)],
) -> AssignPackagesToRouteResponse:
    """Assign packages to a delivery route.

    Args:
        route_id: Identifier of the route receiving packages.
        request: Package identifiers to assign.
        use_case: Use case for assigning packages to a route, injected by FastAPI.

    Returns:
        Per-package assignment successes and errors.

    Raises:
        HTTPException 403: If the caller lacks permission to assign packages.
        HTTPException 404: If the route does not exist.
    """
    try:
        result = use_case.execute(route_id=route_id, package_ids=request.package_ids)
        return _assign_packages_response(result)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@routes_router.patch("/{route_id}/truck", status_code=status.HTTP_200_OK)
def assign_truck_to_route(
    route_id: int,
    request: AssignTruckToRouteRequest,
    use_case: Annotated[AssignTruckToRouteUseCase, Depends(get_assign_truck_to_route_use_case)],
) -> AssignTruckToRouteResponse:
    """Assign a truck to a delivery route.

    Args:
        route_id: Identifier of the route receiving a truck.
        request: Truck identifier to assign.
        use_case: Use case for assigning a truck to a route, injected by FastAPI.

    Returns:
        Route and truck identifiers for the successful assignment.

    Raises:
        HTTPException 403: If the caller lacks permission to assign trucks.
        HTTPException 404: If the route or truck does not exist.
        HTTPException 409: If the selected truck conflicts with route assignment rules.
        HTTPException 500: If the database fails to persist assignment state.
    """
    try:
        now = datetime.now()
        result = use_case.execute(truck_id=request.truck_id, route_id=route_id, now=now)
        return AssignTruckToRouteResponse(route_id=result.route_id, truck_id=result.truck_id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@routes_router.get("/{route_id}/suitable-trucks", status_code=status.HTTP_200_OK)
def find_suitable_trucks_for_route(
    route_id: int,
    use_case: Annotated[
        FindSuitableTrucksForRouteUseCase, Depends(get_find_suitable_trucks_for_route_use_case)
    ],
) -> list[TruckResponse]:
    """Return trucks that can currently serve the requested route.

    Args:
        route_id: Identifier of the route to evaluate.
        use_case: Use case for finding suitable trucks, injected by FastAPI.

    Returns:
        Trucks suitable for the requested route.

    Raises:
        HTTPException 403: If the caller lacks permission to find suitable trucks.
        HTTPException 404: If the route does not exist.
        HTTPException 500: If the database fails to fetch route or truck data.
    """
    try:
        trucks = use_case.execute(route_id=route_id)
        return [truck_response(truck) for truck in trucks]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
