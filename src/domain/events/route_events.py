"""Domain events describing delivery-route lifecycle transitions."""

from dataclasses import dataclass
from datetime import datetime

from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.events.base import DomainEvent
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteCreated(DomainEvent):
    """Event recorded when a new delivery route is created."""

    route_id: int
    locations: tuple[LocationCode, ...]
    departure_time: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteScheduled(DomainEvent):
    """Event recorded when a delivery route is scheduled for departure."""

    route_id: int
    departure_time: datetime
    expected_completion_time: datetime


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageAssignedToRoute(DomainEvent):
    """Event recorded when a package is assigned to a delivery route."""

    route_id: int
    package_id: int
    expected_arrival: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageDetachedFromRoute(DomainEvent):
    """Event recorded when a package is detached from a delivery route."""

    route_id: int
    package_id: int
    reason: PackageDetachmentReason


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckAssignedToRoute(DomainEvent):
    """Event recorded when a truck is assigned to a delivery route."""

    route_id: int
    truck_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckReleasedFromRoute(DomainEvent):
    """Event recorded when a truck is released from a delivery route."""

    route_id: int
    truck_id: int
    release_location: LocationCode
    reason: TruckReleaseReason


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteStarted(DomainEvent):
    """Event recorded when a delivery route enters its in-progress state.

    Reconciliation may infer this transition after the scheduled departure
    time has already passed.
    """

    route_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteCompleted(DomainEvent):
    """Event recorded when a delivery route reaches completion.

    Reconciliation may observe this transition directly from either the
    scheduled or in-progress state.
    """

    route_id: int


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteRemoved(DomainEvent):
    """Event recorded when a delivery route is removed from the system."""

    route_id: int
    detached_package_ids: tuple[int, ...]
    released_truck_id: int | None
