"""Row-to-domain mappers for Postgres query results."""

from datetime import datetime
from decimal import Decimal
from typing import TypedDict

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


def map_customer(row: CustomerRow) -> Customer:
    return Customer(
        customer_id=row["customer_id"],
        contact=ContactInfo(
            name=row["name"],
            email=row["email"],
            phone_number=row["phone"]
        )
    )


def map_truck(row: TruckRow) -> Truck:
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
    route = DeliveryRoute(
        *stops,
        route_id=row["route_id"],
        departure_time=row["departure_time"],
    )
    route.status = RouteStatus(row["status"])
    # route.truck linked after trucks are mapped
    return route


def map_package(row: PackageRow, customer: Customer) -> DeliveryPackage:
    package = DeliveryPackage(
        start_location=LocationCode(row["start_location"]),
        end_location=LocationCode(row["end_location"]),
        weight=float(row["weight"]),
        customer=customer,
        package_id=row["package_id"],
    )
    package.status = ItemStatus(row["status"])
    package.current_location = (
        LocationCode(row["current_location"]) if row["current_location"] is not None else None
    )
    package.expected_arrival = row["expected_arrival"]
    # package.route linked after routes are mapped
    return package


def map_user(row: UserRow) -> User:
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
