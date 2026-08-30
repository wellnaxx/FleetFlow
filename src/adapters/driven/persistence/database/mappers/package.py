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
from src.shared.validation import (
    require_int,
    require_optional_int,
    require_optional_naive_datetime,
    require_optional_str,
    require_str,
)


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
        route_id=typed["route_id"],
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
    package_id = require_int(row["package_id"], "package_id")
    start_location = require_str(row["start_location"], "start_location")
    end_location = require_str(row["end_location"], "end_location")
    weight = row["weight"]
    status = require_str(row["status"], "status")
    current_location = require_optional_str(row["current_location"], "current_location")
    expected_arrival = require_optional_naive_datetime(row["expected_arrival"], "expected_arrival")
    customer_id = require_int(row["customer_id"], "customer_id")
    route_id = require_optional_int(row["route_id"], "route_id")

    if not isinstance(weight, Decimal):
        raise TypeError(f"weight: expected Decimal, got {type(weight).__name__}")

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
