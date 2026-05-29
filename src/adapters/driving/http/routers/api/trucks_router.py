from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.use_cases import get_view_all_trucks_use_case
from src.adapters.driving.http.routers.shared import truck_response
from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase

trucks_router = APIRouter(prefix="/trucks", tags=["trucks"])


@trucks_router.get("/", status_code=status.HTTP_200_OK)
def list_trucks(
    use_case: Annotated[ViewAllTrucksUseCase, Depends(get_view_all_trucks_use_case)],
) -> list[TruckResponse]:
    """List all trucks in the fleet.

    Args:
        use_case: Use case for listing trucks, injected by FastAPI.

    Returns:
        Truck response models for the current fleet.

    Raises:
        HTTPException: Raised with:
            * 403 - Insufficient permissions.
            * 500 - Database operation failure.
    """
    try:
        trucks = use_case.execute()
        return [truck_response(truck) for truck in trucks]
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
