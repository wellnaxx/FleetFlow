from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.driving.http.dependencies.use_cases import get_view_all_customers_use_case
from src.adapters.driving.http.schemas.customers import CustomerPageResponse
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase
from src.application.use_cases.pagination import PageQuery

customers_router = APIRouter(prefix="/customers", tags=["customers"])


@customers_router.get("/", status_code=status.HTTP_200_OK)
def list_customers(
    use_case: Annotated[ViewAllCustomersUseCase, Depends(get_view_all_customers_use_case)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    include_total: bool = False,
) -> CustomerPageResponse:
    """List all customers.

    Args:
        use_case: Use case for listing customers, injected by FastAPI.
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
    result = use_case.execute(PageQuery(limit=limit, offset=offset, include_total=include_total))
    return CustomerPageResponse.from_page(result)
