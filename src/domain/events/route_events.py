"""Domain events describing delivery-route lifecycle transitions."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.enums.truck_status import TruckStatus
from src.domain.events.base import DomainEvent
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteCreated(DomainEvent):
    """Event recorded when a new delivery route is created."""
    event_version: ClassVar[int] = 2

    route_id: int
    locations: tuple[LocationCode, ...]
    departure_time: datetime | None
    initial_status: RouteStatus
    expected_completion_time: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteScheduled(DomainEvent):
    """Event recorded when a delivery route is scheduled for departure."""
    event_version: ClassVar[int] = 2

    route_id: int
    previous_status: RouteStatus
    new_status: RouteStatus
    previous_departure_time: datetime | None
    new_departure_time: datetime
    previous_expected_completion_time: datetime | None
    new_expected_completion_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageAssignedToRoute(DomainEvent):
    """Event recorded when a package is assigned to a delivery route."""
    event_version: ClassVar[int] = 2

    package_id: int
    previous_route_id: int | None
    new_route_id: int
    previous_expected_arrival: datetime | None
    new_expected_arrival: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageDetachedFromRoute(DomainEvent):
    """Event recorded when a package is detached from a delivery route."""
    event_version: ClassVar[int] = 2

    package_id: int
    previous_route_id: int
    new_route_id: int | None
    previous_status: ItemStatus
    new_status: ItemStatus
    previous_location: LocationCode
    new_location: LocationCode
    previous_expected_arrival: datetime | None
    new_expected_arrival: datetime | None
    reason: PackageDetachmentReason


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckAssignedToRoute(DomainEvent):
    """Event recorded when a truck is assigned to a delivery route."""
    event_version: ClassVar[int] = 2

    truck_id: int
    previous_route_id: int | None
    new_route_id: int
    previous_status: TruckStatus
    new_status: TruckStatus
    previous_location: LocationCode
    new_location: LocationCode
    previous_busy_from: datetime | None
    new_busy_from: datetime | None
    previous_busy_until: datetime | None
    new_busy_until: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckReleasedFromRoute(DomainEvent):
    """Event recorded when a truck is released from a delivery route."""
    event_version: ClassVar[int] = 2

    truck_id: int
    previous_route_id: int
    new_route_id: int | None
    previous_status: TruckStatus
    new_status: TruckStatus
    previous_location: LocationCode
    new_location: LocationCode
    previous_busy_from: datetime | None
    new_busy_from: datetime | None
    previous_busy_until: datetime | None
    new_busy_until: datetime | None
    reason: TruckReleaseReason


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteStarted(DomainEvent):
    """Event recorded when a delivery route enters its in-progress state.

    Reconciliation may infer this transition after the scheduled departure
    time has already passed.
    """
    event_version: ClassVar[int] = 2

    route_id: int
    previous_status: RouteStatus
    new_status: RouteStatus


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteCompleted(DomainEvent):
    """Event recorded when a delivery route reaches completion.

    Reconciliation may observe this transition directly from either the
    scheduled or in-progress state.
    """
    event_version: ClassVar[int] = 2

    route_id: int
    previous_status: RouteStatus
    new_status: RouteStatus
    departure_time: datetime
    expected_completion_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteRemoved(DomainEvent):
    """Event recorded when a delivery route is removed from the system."""
    event_version: ClassVar[int] = 2

    route_id: int
    previous_status: RouteStatus
    previous_locations: tuple[LocationCode, ...]
    previous_departure_time: datetime | None
    previous_expected_completion_time: datetime | None
    detached_package_ids: tuple[int, ...]
    released_truck_id: int | None
