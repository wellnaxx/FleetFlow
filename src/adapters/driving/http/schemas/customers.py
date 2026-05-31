from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt


class CustomerResponse(BaseModel):
    """Response model for a customer."""

    customer_id: PositiveInt
    name: str
    email: str = Field(description="Customer email address, or empty when not provided.")
    phone_number: str = Field(description="Customer phone number, or empty when not provided.")


class CustomerPageResponse(BaseModel):
    """Paginated response model for customer listings."""

    items: list[CustomerResponse]
    total: NonNegativeInt | None = None
    count: NonNegativeInt
    limit: PositiveInt | None = None
    offset: NonNegativeInt
