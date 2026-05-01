"""Row-to-domain mappers for Postgres query results."""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.contact_info import ContactInfo
from src.domain.value_objects.location_code import LocationCode


class CustomerRow(TypedDict):
    customer_id: int
    name: str
    email: str
    phone: str


class TruckRow(TypedDict):
    vehicle_id: int
    name: str
    capacity: int
    max_range: int
    status: str
    current_location: str | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: str | None


class RouteRow(TypedDict):
    route_id: int
    departure_time: datetime | None
    status: str
    truck_vehicle_id: int | None


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


class UserRow(TypedDict):
    user_id: int
    username: str
    role: str
    name: str
    email: str
    phone: str
    password_hash: str


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

    if not isinstance(customer_id, int):
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


def map_truck(row: TruckRow) -> Truck:
    """Map a database truck row to a truck entity.

    Args:
        row: Typed database row for a truck.

    Returns:
        Truck entity built from the database row.

    Raises:
        ValueError: If persisted enum or location values are invalid.
    """
    truck = Truck(
        vehicle_id=row["vehicle_id"],
        name=row["name"],
        capacity=row["capacity"],
        max_range=row["max_range"],
    )
    truck.status = TruckStatus(row["status"])
    truck.current_location = (
        LocationCode(row["current_location"]) if row["current_location"] is not None else None
    )
    truck.busy_from = row["busy_from"]
    truck.busy_until = row["busy_until"]
    truck.in_transit_to = LocationCode(row["in_transit_to"]) if row["in_transit_to"] is not None else None
    # truck.route linked after routes are mapped
    return truck


def map_route(row: RouteRow, stops: list[LocationCode]) -> DeliveryRoute:
    """Map a database route row and ordered stops to a route entity.

    Args:
        row: Typed database row for a route.
        stops: Ordered route stops already converted to location codes.

    Returns:
        Delivery route entity built from the database row and stops.

    Raises:
        ValueError: If the route status is invalid or route construction fails.
    """
    route = DeliveryRoute(
        *stops,
        route_id=row["route_id"],
        departure_time=row["departure_time"],
    )
    route.status = RouteStatus(row["status"])
    # route.truck linked after trucks are mapped
    return route


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
    typed = _as_package_row(row)
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
    # package.route linked after routes are mapped
    return package


def _as_package_row(row: RowDict) -> PackageRow:
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

    if not isinstance(package_id, int):
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
    if not isinstance(customer_id, int):
        raise TypeError(f"customer_id: expected int, got {type(customer_id).__name__}")
    if route_id is not None and not isinstance(route_id, int):
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


def map_user(row: UserRow) -> User:
    """Map a database user row to the matching user entity subtype.

    Args:
        row: Typed database row for a user.

    Returns:
        Manager or employee entity based on the stored role.

    Raises:
        ValueError: If the stored role is invalid.
    """
    role = Role(row["role"])
    if role == Role.MANAGER:
        return Manager(
            name=row["name"],
            email=row["email"],
            phone_number=row["phone"],
            user_id=row["user_id"],
        )
    return Employee(
        name=row["name"],
        email=row["email"],
        phone_number=row["phone"],
        user_id=row["user_id"],
    )
