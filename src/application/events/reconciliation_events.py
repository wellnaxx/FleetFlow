"""Application events describing schedule-derived state reconciliation."""

from dataclasses import dataclass
from datetime import datetime

from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.events.base import ApplicationEvent
from src.domain.entities.delivery_route import RoutePositionKind
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode


@dataclass(frozen=True, slots=True, kw_only=True)
class RouteStateReconciled(ApplicationEvent):
    """Record a direct schedule-derived correction to route status."""

    route_id: int
    previous_status: RouteStatus
    new_status: RouteStatus
    departure_time: datetime | None
    expected_completion_time: datetime | None
    reasons: tuple[RouteReconciliationReason, ...]

    def __post_init__(self) -> None:
        """Require at least one unique reason for the reconciliation."""
        if not self.reasons:
            raise ValueError("Route reconciliation requires at least one reason.")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("Route reconciliation reasons must be unique.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageStateReconciled(ApplicationEvent):
    """Record direct package repairs not represented by lifecycle events."""

    package_id: int
    route_id: int | None
    previous_status: ItemStatus
    new_status: ItemStatus
    previous_location: LocationCode
    new_location: LocationCode
    previous_expected_arrival: datetime | None
    new_expected_arrival: datetime | None
    scheduled_pickup_time: datetime | None
    scheduled_delivery_time: datetime | None
    reasons: tuple[PackageReconciliationReason, ...]

    def __post_init__(self) -> None:
        """Require at least one unique reason for the reconciliation."""
        if not self.reasons:
            raise ValueError("Package reconciliation requires at least one reason.")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("Package reconciliation reasons must be unique.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckPositionReconciled(ApplicationEvent):
    """Record a truck position correction derived from its route schedule."""

    truck_id: int
    route_id: int | None
    previous_location: LocationCode | None
    new_location: LocationCode | None
    previous_in_transit_to: LocationCode | None
    new_in_transit_to: LocationCode | None
    position_kind: RoutePositionKind
