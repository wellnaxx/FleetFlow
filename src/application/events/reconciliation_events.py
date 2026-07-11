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
    """Record a direct schedule-derived correction to route status.

    Attributes:
        route_id: Corrected route identifier.
        previous_status: Route status before reconciliation.
        new_status: Route status after reconciliation.
        departure_time: Scheduled departure supporting the correction.
        expected_completion_time: Scheduled completion supporting the correction.
        reason: Reason the direct correction was required.
    """

    route_id: int
    previous_status: RouteStatus
    new_status: RouteStatus
    departure_time: datetime | None
    expected_completion_time: datetime | None
    reason: RouteReconciliationReason


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageStateReconciled(ApplicationEvent):
    """Record direct package repairs not represented by lifecycle events.

    Attributes:
        package_id: Corrected package identifier.
        route_id: Assigned route identifier, if one exists.
        previous_status: Package status before reconciliation.
        new_status: Package status after reconciliation.
        previous_location: Package location before reconciliation.
        new_location: Package location after reconciliation.
        previous_expected_arrival: Expected arrival before reconciliation.
        new_expected_arrival: Expected arrival after reconciliation.
        scheduled_pickup_time: Reconstructed pickup time, if available.
        scheduled_delivery_time: Reconstructed delivery time, if available.
        reasons: Unique reasons contributing to the direct correction.
    """

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
        """Validate the package reconciliation reasons.

        Raises:
            ValueError: If no reason is supplied or a reason occurs more than
                once.
        """
        if not self.reasons:
            raise ValueError("Package reconciliation requires at least one reason.")
        if len(set(self.reasons)) != len(self.reasons):
            raise ValueError("Package reconciliation reasons must be unique.")


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckPositionReconciled(ApplicationEvent):
    """Record a truck position correction derived from its route schedule.

    Attributes:
        truck_id: Corrected truck identifier.
        route_id: Route used to derive the position, if available.
        previous_location: Truck location before reconciliation.
        new_location: Truck location after reconciliation.
        previous_in_transit_to: Transit target before reconciliation.
        new_in_transit_to: Transit target after reconciliation.
        position_kind: Schedule position that caused the correction.
    """

    truck_id: int
    route_id: int | None
    previous_location: LocationCode | None
    new_location: LocationCode | None
    previous_in_transit_to: LocationCode | None
    new_in_transit_to: LocationCode | None
    position_kind: RoutePositionKind


@dataclass(frozen=True, slots=True, kw_only=True)
class TruckRouteReferenceReconciled(ApplicationEvent):
    """Record restoration of a truck's missing route back-reference.

    Attributes:
        truck_id: Corrected truck identifier.
        previous_route_id: Route reference before reconciliation.
        new_route_id: Restored route identifier.
    """

    truck_id: int
    previous_route_id: int | None
    new_route_id: int
