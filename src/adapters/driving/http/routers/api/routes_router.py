from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
from src.adapters.driving.http.dependencies.message_buses import (
    get_authenticated_command_bus,
    get_authenticated_query_bus,
)
from src.adapters.driving.http.dependencies.use_cases import (
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
from src.application.commands.routes.assign_packages_to_route import (
    ASSIGN_PACKAGES_TO_ROUTE,
    AssignPackagesToRouteCommand,
)
from src.application.commands.routes.assign_truck_to_route import (
    ASSIGN_TRUCK_TO_ROUTE,
    AssignTruckToRouteCommand,
)
from src.application.commands.routes.create_route import CREATE_ROUTE, CreateRouteCommand
from src.application.commands.routes.remove_route import REMOVE_ROUTE, RemoveRouteCommand
from src.application.eventing.collector import EventCollector
from src.application.queries.routes.find_suitable_trucks_for_route import (
    FIND_SUITABLE_TRUCKS_FOR_ROUTE,
    FindSuitableTrucksForRouteQuery,
)
from src.application.use_cases.pagination import PageQuery
from src.application.use_cases.routes.view_all_routes import ViewAllRoutesUseCase
from src.application.use_cases.routes.view_route import ViewRouteUseCase
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.ports.input.command_bus import CommandBus
from src.ports.input.query_bus import QueryBus

routes_router = APIRouter(prefix="/routes", tags=["routes"])


@routes_router.post("/", status_code=status.HTTP_201_CREATED)
def create_route(
    request: RouteCreateRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> RouteResponse:
    """Create a new delivery route.

    Args:
        request: The request body containing route creation details.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns application and domain-event publication.

    Returns:
        The created route details.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid route creation input.
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    route = command_bus.dispatch(
        key=CREATE_ROUTE,
        command=CreateRouteCommand(
            locations=tuple(request.locations),
            departure_time=request.departure_time,
        ),
    )
    return RouteResponse.from_route(route)


@routes_router.get("/", status_code=status.HTTP_200_OK)
def list_routes(
    use_case: Annotated[ViewAllRoutesUseCase, Depends(get_view_all_routes_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> RoutePageResponse:
    """List delivery routes with pagination.

    Args:
        use_case: Use case for listing routes, injected by FastAPI.
        event_collector: Collector used to publish authorization events.
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
    result = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(PageQuery(limit=limit, offset=offset, include_total=include_total)),
    )
    return RoutePageResponse.from_page(result)


@routes_router.get("/in-progress", status_code=status.HTTP_200_OK)
def list_in_progress_routes(
    use_case: Annotated[ViewRoutesInProgressUseCase, Depends(get_view_routes_in_progress_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> list[RouteInProgressResponse]:
    """List routes that are currently at a stop or in transit.

    Args:
        use_case: Use case for listing active routes, injected by FastAPI.
        event_collector: Collector used to publish authorization events.

    Returns:
        Active route details with computed position information.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    # Domain route timing currently uses naive local datetimes.
    now = datetime.now()
    active_routes = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(now=now),
    )
    try:
        return [
            RouteInProgressResponse.from_route_position(route, position) for route, position in active_routes
        ]
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Route position calculation failed.",
        ) from exc


@routes_router.get("/{route_id}", status_code=status.HTTP_200_OK)
def get_route(
    route_id: int,
    use_case: Annotated[ViewRouteUseCase, Depends(get_view_route_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> RouteResponse:
    """Return one delivery route by id.

    Args:
        route_id: Identifier of the route to retrieve.
        use_case: Use case for retrieving one route, injected by FastAPI.
        event_collector: Collector used to publish authorization events.

    Returns:
        Route details for the requested route.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    route = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(route_id=route_id),
    )
    return RouteResponse.from_route(route)


@routes_router.delete("/{route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_route(
    route_id: int,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> None:
    """Remove one delivery route by id.

    Args:
        route_id: Identifier of the route to remove.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns authorization and domain-event
            publication.

    Returns:
        None.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    command_bus.dispatch(
        key=REMOVE_ROUTE,
        command=RemoveRouteCommand(route_id=route_id),
    )


@routes_router.patch("/{route_id}/packages", status_code=status.HTTP_200_OK)
def assign_packages_to_route(
    route_id: int,
    request: AssignPackagesToRouteRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> AssignPackagesToRouteResponse:
    """Assign packages to a delivery route.

    Args:
        route_id: Identifier of the route receiving packages.
        request: Package identifiers to assign.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns application and domain-event publication.

    Returns:
        Per-package assignment successes and errors.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    result = command_bus.dispatch(
        key=ASSIGN_PACKAGES_TO_ROUTE,
        command=AssignPackagesToRouteCommand(
            route_id=route_id,
            package_ids=tuple(request.package_ids),
        ),
    )

    return AssignPackagesToRouteResponse.from_result(result)


@routes_router.patch("/{route_id}/truck", status_code=status.HTTP_200_OK)
def assign_truck_to_route(
    route_id: int,
    request: AssignTruckToRouteRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> AssignTruckToRouteResponse:
    """Assign a truck to a delivery route.

    Args:
        route_id: Identifier of the route receiving a truck.
        request: Truck identifier to assign.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns application and domain-event publication.

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
    result = command_bus.dispatch(
        key=ASSIGN_TRUCK_TO_ROUTE,
        command=AssignTruckToRouteCommand(
            truck_id=request.truck_id,
            route_id=route_id,
            now=now,
        ),
    )
    return AssignTruckToRouteResponse.from_result(result)


@routes_router.get("/{route_id}/suitable-trucks", status_code=status.HTTP_200_OK)
def find_suitable_trucks_for_route(
    route_id: int,
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
) -> list[TruckResponse]:
    """Return trucks that can currently serve the requested route.

    Args:
        route_id: Identifier of the route to evaluate.
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.

    Returns:
        Trucks suitable for the requested route.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 404 - Route not found.
            * 500 - Database operation failure.
    """
    trucks = query_bus.dispatch(
        key=FIND_SUITABLE_TRUCKS_FOR_ROUTE,
        query=FindSuitableTrucksForRouteQuery(route_id=route_id),
    )
    return [TruckResponse.from_truck(truck) for truck in trucks]
