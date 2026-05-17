"""Row-to-domain mappers for Postgres query results."""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.application.models.user_record import UserRecord
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck
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


class RouteStopRow(TypedDict):
    stop_order: int
    location_code: str


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


class UserRecordRow(TypedDict):
    user_id: int
    username: str
    role: str
    name: str
    email: str
    phone: str
    password_hash: str
    token_version: int


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


def map_truck(row: RowDict) -> Truck:
    """Map a database truck row to a truck entity.

    Args:
        row: Column-name-keyed database row for a truck.

    Returns:
        Truck entity built from the database row.

    Raises:
        KeyError: If a required truck column is missing.
        TypeError: If a required truck column has an unexpected type.
        ValueError: If persisted enum or location values are invalid.
    """
    typed = _as_truck_row(row)
    truck = Truck(
        vehicle_id=typed["vehicle_id"],
        name=typed["name"],
        capacity=typed["capacity"],
        max_range=typed["max_range"],
    )
    truck.status = TruckStatus(typed["status"])
    truck.current_location = (
        LocationCode(typed["current_location"]) if typed["current_location"] is not None else None
    )
    truck.busy_from = typed["busy_from"]
    truck.busy_until = typed["busy_until"]
    truck.in_transit_to = LocationCode(typed["in_transit_to"]) if typed["in_transit_to"] is not None else None
    # truck.route linked after routes are mapped
    return truck


def _as_truck_row(row: RowDict) -> TruckRow:
    """Validate and narrow a generic database row to a truck row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed truck row with validated field types.

    Raises:
        KeyError: If a required truck column is missing.
        TypeError: If a required truck column has an unexpected type.
    """
    vehicle_id = row["vehicle_id"]
    name = row["name"]
    capacity = row["capacity"]
    max_range = row["max_range"]
    status = row["status"]
    current_location = row["current_location"]
    busy_from = row["busy_from"]
    busy_until = row["busy_until"]
    in_transit_to = row["in_transit_to"]

    if not isinstance(vehicle_id, int) or isinstance(vehicle_id, bool):
        raise TypeError(f"vehicle_id: expected int, got {type(vehicle_id).__name__}")
    if not isinstance(name, str):
        raise TypeError(f"name: expected str, got {type(name).__name__}")
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise TypeError(f"capacity: expected int, got {type(capacity).__name__}")
    if not isinstance(max_range, int) or isinstance(max_range, bool):
        raise TypeError(f"max_range: expected int, got {type(max_range).__name__}")
    if not isinstance(status, str):
        raise TypeError(f"status: expected str, got {type(status).__name__}")
    if current_location is not None and not isinstance(current_location, str):
        raise TypeError(f"current_location: expected str or None, got {type(current_location).__name__}")
    if busy_from is not None and not isinstance(busy_from, datetime):
        raise TypeError(f"busy_from: expected datetime or None, got {type(busy_from).__name__}")
    if busy_until is not None and not isinstance(busy_until, datetime):
        raise TypeError(f"busy_until: expected datetime or None, got {type(busy_until).__name__}")
    if in_transit_to is not None and not isinstance(in_transit_to, str):
        raise TypeError(f"in_transit_to: expected str or None, got {type(in_transit_to).__name__}")

    return TruckRow(
        vehicle_id=vehicle_id,
        name=name,
        capacity=capacity,
        max_range=max_range,
        status=status,
        current_location=current_location,
        busy_from=busy_from,
        busy_until=busy_until,
        in_transit_to=in_transit_to,
    )


def map_route(rows: list[RowDict]) -> DeliveryRoute:
    """Map a database route row and ordered stops to a route entity.

    Args:
        rows: Ordered route query rows. Each row contains the same route fields
            and one route stop.

    Returns:
        Delivery route entity built from the database row and stops.

    Raises:
        KeyError: If a required route or stop column is missing.
        TypeError: If a required route or stop column has an unexpected type.
        ValueError: If the route status is invalid or route construction fails.
    """
    if not rows:
        raise ValueError("Cannot map a route without route rows.")

    typed = as_route_row(rows[0])
    stops = [LocationCode(as_route_stop_row(row)["location_code"]) for row in rows]
    route = DeliveryRoute(
        *stops,
        route_id=typed["route_id"],
        departure_time=typed["departure_time"],
    )
    route.status = RouteStatus(typed["status"])
    # route.truck linked after trucks are mapped
    return route


def as_route_row(row: RowDict) -> RouteRow:
    """Validate and narrow a generic database row to a route row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed route row with validated field types.

    Raises:
        KeyError: If a required route column is missing.
        TypeError: If a required route column has an unexpected type.
    """
    route_id = row["route_id"]
    departure_time = row["departure_time"]
    status = row["status"]
    truck_vehicle_id = row["truck_vehicle_id"]

    if not isinstance(route_id, int) or isinstance(route_id, bool):
        raise TypeError(f"route_id: expected int, got {type(route_id).__name__}")
    if departure_time is not None and not isinstance(departure_time, datetime):
        raise TypeError(f"departure_time: expected datetime or None, got {type(departure_time).__name__}")
    if not isinstance(status, str):
        raise TypeError(f"status: expected str, got {type(status).__name__}")
    if truck_vehicle_id is not None and (
        not isinstance(truck_vehicle_id, int) or isinstance(truck_vehicle_id, bool)
    ):
        raise TypeError(f"truck_vehicle_id: expected int or None, got {type(truck_vehicle_id).__name__}")

    return RouteRow(
        route_id=route_id,
        departure_time=departure_time,
        status=status,
        truck_vehicle_id=truck_vehicle_id,
    )


def as_route_stop_row(row: RowDict) -> RouteStopRow:
    """Validate and narrow a generic database row to a route stop row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed route stop row with validated field types.

    Raises:
        KeyError: If a required route stop column is missing.
        TypeError: If a required route stop column has an unexpected type.
    """
    stop_order = row["stop_order"]
    location_code = row["location_code"]

    if not isinstance(stop_order, int) or isinstance(stop_order, bool):
        raise TypeError(f"stop_order: expected int, got {type(stop_order).__name__}")
    if not isinstance(location_code, str):
        raise TypeError(f"location_code: expected str, got {type(location_code).__name__}")

    return RouteStopRow(
        stop_order=stop_order,
        location_code=location_code,
    )


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
    # package.route linked after routes are mapped
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


def map_user_record(row: RowDict) -> UserRecord:
    """Map a database user row to a UserRecord.

    The password hash is preserved on UserRecord for AuthService.
    The User session entity is constructed by AuthService after
    credential verification, not here.

    Args:
        row: Typed database row for a user.

    Returns:
        UserRecord carrying contact info, role, and password hash.

    Raises:
        KeyError: If a required user column is missing.
        TypeError: If a required user column has an unexpected type.
        ValueError: If the token_version is not positive.
    """
    typed = _as_user_record_row(row)
    return UserRecord(
        user_id=typed["user_id"],
        username=typed["username"],
        role=typed["role"],
        name=typed["name"],
        email=typed["email"],
        phone_number=typed["phone"],
        password=typed["password_hash"],
        token_version=typed["token_version"],
    )


def _as_user_record_row(row: RowDict) -> UserRecordRow:
    """Validate and narrow a generic database row to a user record row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed user record row with validated field types.

    Raises:
        KeyError: If a required user column is missing.
        TypeError: If a required user column has an unexpected type.
        ValueError: If the token_version is not positive.
    """
    user_id = row["user_id"]
    username = row["username"]
    role = row["role"]
    name = row["name"]
    email = row["email"]
    phone_number = row["phone"]
    password_hash = row["password_hash"]
    token_version = row["token_version"]

    if not isinstance(user_id, int) or isinstance(user_id, bool):
        raise TypeError(f"user_id: expected int, got {type(user_id).__name__}")
    if not isinstance(username, str):
        raise TypeError(f"username: expected str, got {type(username).__name__}")
    if not isinstance(role, str):
        raise TypeError(f"role: expected str, got {type(role).__name__}")
    if not isinstance(name, str):
        raise TypeError(f"name: expected str, got {type(name).__name__}")
    if not isinstance(email, str):
        raise TypeError(f"email: expected str, got {type(email).__name__}")
    if not isinstance(phone_number, str):
        raise TypeError(f"phone: expected str, got {type(phone_number).__name__}")
    if not isinstance(password_hash, str):
        raise TypeError(f"password_hash: expected str, got {type(password_hash).__name__}")
    if not isinstance(token_version, int) or isinstance(token_version, bool):
        raise TypeError(f"token_version: expected int, got {type(token_version).__name__}")
    if token_version < 1:
        raise ValueError("token_version must be positive")

    return UserRecordRow(
        user_id=user_id,
        username=username,
        role=role,
        name=name,
        email=email,
        phone=phone_number,
        password_hash=password_hash,
        token_version=token_version,
    )
