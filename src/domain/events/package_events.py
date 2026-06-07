"""Domain events describing delivery-package lifecycle transitions."""

from dataclasses import dataclass

from src.domain.events.base import DomainEvent
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageCreated(DomainEvent):
    """Event recorded when a new package is created."""

    package_id: int
    customer_id: int
    start_location: LocationCode
    end_location: LocationCode
    weight: float


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageRemoved(DomainEvent):
    """Event recorded when a package is removed from the system."""

    package_id: int
    customer_id: int
    route_id: int | None


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePickedUp(DomainEvent):
    """Event recorded when a package enters its in-progress lifecycle state.

    Reconciliation may infer this transition after the scheduled pickup time
    has already passed.
    """

    package_id: int
    route_id: int
    pickup_location: LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageDelivered(DomainEvent):
    """Event recorded when a package reaches its delivery destination.

    Reconciliation may observe this transition directly from either the to-do
    or in-progress state.
    """

    package_id: int
    route_id: int
    delivery_location: LocationCode
