"""Database row mappers for customers."""

from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo


class CustomerRow(TypedDict):
    customer_id: int
    name: str
    email: str
    phone: str


def map_customer(row: RowDict) -> Customer:
    """Map a database customer row to a customer entity.

    Args:
        row: Column-name-keyed database row for a customer.

    Returns:
        Customer entity built from the database row.

    Raises:
        KeyError: If a required customer column is missing.
        TypeError: If a required customer column has an unexpected type.
        ValueError: If the row contains invalid contact information.
    """
    typed = _as_customer_row(row)
    return Customer(
        customer_id=typed["customer_id"],
        contact=ContactInfo(name=typed["name"], email=typed["email"], phone_number=typed["phone"]),
    )


def _as_customer_row(row: RowDict) -> CustomerRow:
    """Validate and narrow a generic database row to a customer row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed customer row with validated field types.

    Raises:
        KeyError: If a required customer column is missing.
        TypeError: If a required customer column has an unexpected type.
    """
    customer_id = row["customer_id"]
    name = row["name"]
    email = row["email"]
    phone = row["phone"]

    if not isinstance(customer_id, int) or isinstance(customer_id, bool):
        raise TypeError(f"customer_id: expected int, got {type(customer_id).__name__}")
    if not isinstance(name, str):
        raise TypeError(f"name: expected str, got {type(name).__name__}")
    if not isinstance(email, str):
        raise TypeError(f"email: expected str, got {type(email).__name__}")
    if not isinstance(phone, str):
        raise TypeError(f"phone: expected str, got {type(phone).__name__}")

    return CustomerRow(
        customer_id=customer_id,
        name=name,
        email=email,
        phone=phone,
    )
