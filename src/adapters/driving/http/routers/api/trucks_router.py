from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.adapters.driving.http.dependencies.message_buses import get_authenticated_query_bus
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.application.queries.trucks.view_all_trucks import VIEW_ALL_TRUCKS, ViewAllTrucksQuery
from src.ports.input.query_bus import QueryBus

trucks_router = APIRouter(prefix="/trucks", tags=["trucks"])


@trucks_router.get("/", status_code=status.HTTP_200_OK)
def list_trucks(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
) -> list[TruckResponse]:
    """List all trucks in the fleet.

    Args:
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.

    Returns:
        Truck response models for the current fleet.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    trucks = query_bus.dispatch(
        key=VIEW_ALL_TRUCKS,
        query=ViewAllTrucksQuery(),
    )
    return [TruckResponse.from_truck(truck) for truck in trucks]
