from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.driving.http.dependencies.use_cases import get_view_all_customers_use_case
from src.adapters.driving.http.schemas.customers import CustomerResponse
from src.application.use_cases.customers.view_all_customers import ViewAllCustomersUseCase

customers_router = APIRouter(prefix="/customers", tags=["customers"])


@customers_router.get("/", status_code=status.HTTP_200_OK)
def list_customers(
    use_case: Annotated[ViewAllCustomersUseCase, Depends(get_view_all_customers_use_case)],
) -> list[CustomerResponse]:
    """List all customers.

    Args:
        use_case: Use case for listing customers, injected by FastAPI.

    Returns:
        A list of customers, or an empty list if no customers exist.

    Raises:
        HTTPException: If the caller lacks permission to view customers.
    """
    try:
        customers = use_case.execute()
        return [
            CustomerResponse(
                customer_id=customer.customer_id,
                name=customer.name,
                email=customer.email,
                phone_number=customer.phone_number,
            )
            for customer in customers
        ]
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e
