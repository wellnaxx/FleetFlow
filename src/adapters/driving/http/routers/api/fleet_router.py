"""HTTP routes for retrieving fleet overview projections."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.message_buses import get_authenticated_query_bus
from src.adapters.driving.http.schemas.fleet import FleetOverviewResponse
from src.application.queries.fleet.get_fleet_overview import (
    GET_FLEET_OVERVIEW,
    GetFleetOverviewQuery,
)
from src.ports.input.query_bus import QueryBus

fleet_router = APIRouter(prefix="/fleet", tags=["fleet"])


@fleet_router.get("/overview", status_code=status.HTTP_200_OK)
def get_fleet_overview(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
    active_route_limit: Annotated[
        int,
        Query(
            ge=1,
            le=100,
            description="Maximum number of active-route details to include.",
        ),
    ] = 10,
) -> FleetOverviewResponse:
    """Return an authorized point-in-time fleet operations overview.

    Args:
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.
        active_route_limit: Maximum active-route projections to include.

    Returns:
        Package, route, truck, and active-route operational summaries.

    Raises:
        PermissionError: If the current principal cannot view fleet overviews.
        ValidationError: If the request or persisted projection is invalid.
        DatabaseError: If the persistence query fails.
        RuntimeError: If persisted active-route scheduling data cannot be
            projected.
    """
    result = query_bus.dispatch(
        key=GET_FLEET_OVERVIEW,
        query=GetFleetOverviewQuery(active_route_limit=active_route_limit),
    )

    return FleetOverviewResponse.from_overview(result)
