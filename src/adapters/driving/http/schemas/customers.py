from pydantic import BaseModel, Field, PositiveInt


class CustomerResponse(BaseModel):
    """Response model for a customer."""

    customer_id: PositiveInt
    name: str
    email: str = Field(description="Customer email address, or empty when not provided.")
    phone_number: str = Field(description="Customer phone number, or empty when not provided.")
