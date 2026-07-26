"""HTTP routes for retrieving fleet overview projections."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
from src.adapters.driving.http.dependencies.use_cases import get_fleet_overview_use_case
from src.adapters.driving.http.schemas.fleet import FleetOverviewResponse
from src.application.eventing.collector import EventCollector
from src.application.use_cases.fleet.get_overview import GetFleetOverviewUseCase

fleet_router = APIRouter(prefix="/fleet", tags=["fleet"])


@fleet_router.get("/overview", status_code=status.HTTP_200_OK)
def get_fleet_overview(
    use_case: Annotated[GetFleetOverviewUseCase, Depends(get_fleet_overview_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
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
        use_case: Fleet-overview use case bound to the authenticated principal.
        event_collector: Collector used to publish authorization events.
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
    result = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=lambda: use_case.execute(active_route_limit=active_route_limit),
    )

    return FleetOverviewResponse.from_overview(result)
