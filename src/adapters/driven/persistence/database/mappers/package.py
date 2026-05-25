"""Database row mappers for packages."""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.adapters.driven.persistence.database.mappers.customer import map_customer
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.enums.item_status import ItemStatus
from src.domain.value_objects.location_code import LocationCode


class PackageRow(TypedDict):
    package_id: int
    start_location: str
    end_location: str
    weight: Decimal
    status: str
    current_location: str | None
    expected_arrival: datetime | None
    customer_id: int
    route_id: int | None


def map_package(row: RowDict, customer: Customer) -> DeliveryPackage:
    """Map a database package row to a delivery package entity.

    Args:
        row: Column-name-keyed database row for a package.
        customer: Customer entity referenced by the package row.

    Returns:
        Delivery package entity built from the database row.

    Raises:
        KeyError: If a required package column is missing.
        TypeError: If a required package column has an unexpected type.
        ValueError: If persisted enum or location values are invalid.
    """
    typed = as_package_row(row)
    package = DeliveryPackage(
        start_location=LocationCode(typed["start_location"]),
        end_location=LocationCode(typed["end_location"]),
        weight=float(typed["weight"]),
        customer=customer,
        package_id=typed["package_id"],
    )
    package.status = ItemStatus(typed["status"])
    package.current_location = (
        LocationCode(typed["current_location"]) if typed["current_location"] is not None else None
    )
    package.expected_arrival = typed["expected_arrival"]
    return package


def as_package_row(row: RowDict) -> PackageRow:
    """Validate and narrow a generic database row to a package row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed package row with validated field types.

    Raises:
        KeyError: If a required package column is missing.
        TypeError: If a required package column has an unexpected type.
    """
    package_id = row["package_id"]
    start_location = row["start_location"]
    end_location = row["end_location"]
    weight = row["weight"]
    status = row["status"]
    current_location = row["current_location"]
    expected_arrival = row["expected_arrival"]
    customer_id = row["customer_id"]
    route_id = row["route_id"]

    if not isinstance(package_id, int) or isinstance(package_id, bool):
        raise TypeError(f"package_id: expected int, got {type(package_id).__name__}")
    if not isinstance(start_location, str):
        raise TypeError(f"start_location: expected str, got {type(start_location).__name__}")
    if not isinstance(end_location, str):
        raise TypeError(f"end_location: expected str, got {type(end_location).__name__}")
    if not isinstance(weight, Decimal):
        raise TypeError(f"weight: expected Decimal, got {type(weight).__name__}")
    if not isinstance(status, str):
        raise TypeError(f"status: expected str, got {type(status).__name__}")
    if current_location is not None and not isinstance(current_location, str):
        raise TypeError(f"current_location: expected str or None, got {type(current_location).__name__}")
    if expected_arrival is not None and not isinstance(expected_arrival, datetime):
        raise TypeError(f"expected_arrival: expected datetime or None, got {type(expected_arrival).__name__}")
    if not isinstance(customer_id, int) or isinstance(customer_id, bool):
        raise TypeError(f"customer_id: expected int, got {type(customer_id).__name__}")
    if route_id is not None and (not isinstance(route_id, int) or isinstance(route_id, bool)):
        raise TypeError(f"route_id: expected int or None, got {type(route_id).__name__}")

    return PackageRow(
        package_id=package_id,
        start_location=start_location,
        end_location=end_location,
        weight=weight,
        status=status,
        current_location=current_location,
        expected_arrival=expected_arrival,
        customer_id=customer_id,
        route_id=route_id,
    )


def map_package_with_customer(row: RowDict) -> DeliveryPackage:
    """Map a joined package/customer row to a delivery package entity.

    Args:
        row: Column-name-keyed database row containing package columns plus
            joined customer columns: customer_name, customer_email, and
            customer_phone.

    Returns:
        Delivery package entity with its customer link restored.

    Raises:
        KeyError: If a required package or customer column is missing.
        TypeError: If a required package or customer column has an unexpected type.
        ValueError: If persisted enum, location, or contact values are invalid.
    """
    customer = map_customer_from_package_row(row)
    package = map_package(row, customer)
    customer.restore_package_link(package)
    return package


def map_customer_from_package_row(row: RowDict) -> Customer:
    """Map joined customer columns from a package/customer query row.

    Args:
        row: Column-name-keyed database row containing package columns plus
            customer_name, customer_email, and customer_phone aliases.

    Returns:
        Customer entity built from the joined customer columns.

    Raises:
        KeyError: If a required customer column is missing.
        TypeError: If a required customer column has an unexpected type.
        ValueError: If the customer contact information is invalid.
    """
    return map_customer(
        {
            "customer_id": row["customer_id"],
            "name": row["customer_name"],
            "email": row["customer_email"],
            "phone": row["customer_phone"],
        }
    )
