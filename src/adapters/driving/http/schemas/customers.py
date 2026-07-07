from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt

from src.application.use_cases.pagination import PageResult
from src.domain.entities.customer import Customer


class CustomerResponse(BaseModel):
    """Response model for a customer."""

    customer_id: PositiveInt
    name: str
    email: str = Field(description="Customer email address, or empty when not provided.")
    phone_number: str = Field(description="Customer phone number, or empty when not provided.")

    @classmethod
    def from_customer(cls, customer: Customer) -> "CustomerResponse":
        """Build an HTTP response from a customer entity.

        Args:
            customer: Domain customer entity returned by a use case.

        Returns:
            Serialized customer response.
        """
        return cls(
            customer_id=customer.customer_id,
            name=customer.name,
            email=customer.email,
            phone_number=customer.phone_number,
        )


class CustomerPageResponse(BaseModel):
    """Paginated response model for customer listings."""

    items: list[CustomerResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt

    @classmethod
    def from_page(cls, page: PageResult[Customer]) -> "CustomerPageResponse":
        """Build a paginated HTTP response from a customer page result.

        Args:
            page: Application page result containing customer entities.

        Returns:
            Serialized customer page response.
        """
        return cls(
            items=[CustomerResponse.from_customer(customer) for customer in page.items],
            total=page.total,
            count=page.count,
            limit=page.limit,
            offset=page.offset,
        )
