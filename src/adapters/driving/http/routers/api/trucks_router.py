from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.adapters.driving.http.dependencies.eventing import execute_and_drain_events, get_event_collector
from src.adapters.driving.http.dependencies.use_cases import get_view_all_trucks_use_case
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.application.eventing.collector import EventCollector
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase

trucks_router = APIRouter(prefix="/trucks", tags=["trucks"])


@trucks_router.get("/", status_code=status.HTTP_200_OK)
def list_trucks(
    use_case: Annotated[ViewAllTrucksUseCase, Depends(get_view_all_trucks_use_case)],
    event_collector: Annotated[EventCollector, Depends(get_event_collector)],
) -> list[TruckResponse]:
    """List all trucks in the fleet.

    Args:
        use_case: Use case for listing trucks, injected by FastAPI.
        event_collector: Collector used to publish authorization events.

    Returns:
        Truck response models for the current fleet.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    trucks = execute_and_drain_events(
        recorder=use_case,
        event_collector=event_collector,
        action=use_case.execute,
    )
    return [TruckResponse.from_truck(truck) for truck in trucks]
