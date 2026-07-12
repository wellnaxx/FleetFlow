from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
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
from src.adapters.driving.http.schemas.routes import (
    AssignPackagesToRouteRequest,
    AssignPackagesToRouteResponse,
    AssignTruckToRouteRequest,
    AssignTruckToRouteResponse,
    RouteCreateRequest,
    RouteInProgressResponse,
    RoutePageResponse,
    RouteResponse,
)
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.application.eventing.collector import EventCollector
from src.application.use_cases.pagination import PageQuery
from src.application.use_cases.routes.assign_packages_to_route import AssignPackagesToRouteUseCase
from src.application.use_cases.routes.assign_truck_to_route import AssignTruckToRouteUseCase
from src.application.use_cases.routes.create_route import CreateRouteUseCase
from src.application.use_cases.routes.find_suitable_trucks_for_route import FindSuitableTrucksForRouteUseCase
from src.application.use_cases.routes.remove_route import RemoveRouteUseCase
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase

routes_router = APIRouter(prefix="/routes", tags=["routes"])


@routes_router.post("/", status_code=status.HTTP_201_CREATED)
def create_route(
    request: RouteCreateRequest,
    use_case: Annotated[CreateRouteUseCase, Depends(get_create_route_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> RouteResponse:
    """Create a new delivery route.

    Args:
        request: The request body containing route creation details.
        use_case: Use case for creating a route, injected by FastAPI.
        event_collector: Collector used to publish route creation events.

    Returns:
        The created route details.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid route creation input.
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    route = use_case.execute(
        locations=request.locations,
        departure_time=request.departure_time,
    )

    event_collector.drain((route,))
    return RouteResponse.from_route(route)


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
        HTTPException: Raised with:
            * 400 - Invalid pagination input.
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    result = use_case.execute(PageQuery(limit=limit, offset=offset, include_total=include_total))
    return RoutePageResponse.from_page(result)


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
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    # Domain route timing currently uses naive local datetimes.
    now = datetime.now()
    active_routes = use_case.execute(now=now)
    try:
        return [
            RouteInProgressResponse.from_route_position(route, position)
            for route, position in active_routes
        ]
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Route position calculation failed.",
        ) from exc


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
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    route = use_case.execute(route_id=route_id)
    return RouteResponse.from_route(route)


@routes_router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    use_case: Annotated[RemoveRouteUseCase, Depends(get_remove_route_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> None:
    """Remove one delivery route by id.

    Args:
        route_id: Identifier of the route to remove.
        use_case: Use case for removing one route, injected by FastAPI.
        event_collector: Collector used to publish route removal events.

    Returns:
        None.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    route = use_case.execute(route_id=route_id)
    event_collector.drain((route,))


@routes_router.patch("/{route_id}/packages", status_code=status.HTTP_200_OK)
def assign_packages_to_route(
    route_id: int,
    request: AssignPackagesToRouteRequest,
    use_case: Annotated[AssignPackagesToRouteUseCase, Depends(get_assign_packages_to_route_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> AssignPackagesToRouteResponse:
    """Assign packages to a delivery route.

    Args:
        route_id: Identifier of the route receiving packages.
        request: Package identifiers to assign.
        use_case: Use case for assigning packages to a route, injected by FastAPI.
        event_collector: Collector used to publish use-case authorization events
            and route package-assignment events.

    Returns:
        Per-package assignment successes and errors.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    result = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(route_id=route_id, package_ids=request.package_ids),
    )

    if result.successes:
        event_collector.drain((result.successes[0].route,))

    return AssignPackagesToRouteResponse.from_result(result)


@routes_router.patch("/{route_id}/truck", status_code=status.HTTP_200_OK)
def assign_truck_to_route(
    route_id: int,
    request: AssignTruckToRouteRequest,
    use_case: Annotated[AssignTruckToRouteUseCase, Depends(get_assign_truck_to_route_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> AssignTruckToRouteResponse:
    """Assign a truck to a delivery route.

    Args:
        route_id: Identifier of the route receiving a truck.
        request: Truck identifier to assign.
        use_case: Use case for assigning a truck to a route, injected by FastAPI.
        event_collector: Collector used to publish use-case authorization events
            and route truck-assignment events.

    Returns:
        Route and truck identifiers for the successful assignment.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route or truck not found.
            * 409 - Truck conflicts with route assignment rules.
            * 500 - Database operation failure.
    """
    # Domain route timing currently uses naive local datetimes.
    now = datetime.now()
    result = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(truck_id=request.truck_id, route_id=route_id, now=now),
    )
    event_collector.drain((result.route,))
    return AssignTruckToRouteResponse.from_result(result)


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
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    trucks = use_case.execute(route_id=route_id)
    return [TruckResponse.from_truck(truck) for truck in trucks]
