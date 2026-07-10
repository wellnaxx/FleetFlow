"""Domain events describing delivery-package lifecycle transitions."""

from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar

from src.domain.enums.item_status import ItemStatus
from src.domain.events.base import DomainEvent
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageCreated(DomainEvent):
    """Event recorded when a new package is created."""
    event_version: ClassVar[int] = 2

    package_id: int
    customer_id: int
    start_location: LocationCode
    end_location: LocationCode
    weight: float
    initial_status: ItemStatus
    initial_location: LocationCode
    expected_arrival: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageRemoved(DomainEvent):
    """Event recorded when a package is removed from the system."""
    event_version: ClassVar[int] = 2

    package_id: int
    customer_id: int
    previous_route_id: int | None
    previous_status: ItemStatus
    previous_location: LocationCode
    start_location: LocationCode
    end_location: LocationCode
    weight: float
    previous_expected_arrival: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePickedUp(DomainEvent):
    """Event recorded when a package enters its in-progress lifecycle state.

    Reconciliation may infer this transition after the scheduled pickup time
    has already passed.
    """
    event_version: ClassVar[int] = 2

    package_id: int
    route_id: int
    previous_status: ItemStatus
    new_status: ItemStatus
    previous_location: LocationCode
    new_location: LocationCode
    scheduled_arrival: datetime | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageDelivered(DomainEvent):
    """Event recorded for the normal in-progress-to-delivered transition."""
    event_version: ClassVar[int] = 2

    package_id: int
    route_id: int
    previous_status: ItemStatus
    new_status: ItemStatus
    previous_location: LocationCode
    new_location: LocationCode
    scheduled_arrival: datetime | None
