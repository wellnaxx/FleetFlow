from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from src.adapters.driving.http.dependencies.use_cases import get_view_all_customers_use_case
from src.adapters.driving.http.schemas.customers import CustomerPageResponse, CustomerResponse
from src.application.exceptions.application_errors import ValidationError
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
        HTTPException: If pagination arguments are invalid or the caller lacks permission to view customers.
    """
    try:
        result = use_case.execute(PageQuery(limit=limit, offset=offset, include_total=include_total))
        items = [
            CustomerResponse(
                customer_id=customer.customer_id,
                name=customer.name,
                email=customer.email,
                phone_number=customer.phone_number,
            )
            for customer in result.items
        ]
        return CustomerPageResponse(
            items=items,
            total=result.total,
            count=result.count,
            limit=result.limit or limit,
            offset=result.offset,
        )
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
