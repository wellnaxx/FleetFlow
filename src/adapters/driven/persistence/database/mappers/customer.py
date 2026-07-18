"""Database row mappers for customers."""

from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.customer import Customer
from src.domain.value_objects.contact_info import ContactInfo
from src.shared.validation import require_int, require_str


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
    customer_id = require_int(row["customer_id"], "customer_id")
    name = require_str(row["name"], "name")
    email = require_str(row["email"], "email")
    phone = require_str(row["phone"], "phone")

    return CustomerRow(
        customer_id=customer_id,
        name=name,
        email=email,
        phone=phone,
    )
