from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.message_buses import get_authenticated_query_bus
from src.adapters.driving.http.schemas.customers import CustomerPageResponse
from src.application.queries.customers.view_all_customers import (
    VIEW_ALL_CUSTOMERS,
    ViewAllCustomersQuery,
)
from src.application.use_cases.pagination import PageQuery
from src.ports.input.query_bus import QueryBus

customers_router = APIRouter(prefix="/customers", tags=["customers"])


@customers_router.get("/", status_code=status.HTTP_200_OK)
def list_customers(
    query_bus: Annotated[QueryBus, Depends(get_authenticated_query_bus)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> CustomerPageResponse:
    """List all customers.

    Args:
        query_bus: Authenticated query bus injected by FastAPI. The registered
            executor owns authorization-event publication.
        limit: Maximum number of customers to return.
        offset: Number of customers to skip.
        include_total: Whether to include the total customer count.

    Returns:
        A paginated customer response.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid pagination input.
            * 403 - Insufficient permissions.
    """
    result = query_bus.dispatch(
        key=VIEW_ALL_CUSTOMERS,
        query=ViewAllCustomersQuery(page=PageQuery(limit=limit, offset=offset, include_total=include_total)),
    )
    return CustomerPageResponse.from_page(result)
