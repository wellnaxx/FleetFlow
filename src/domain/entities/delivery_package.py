"""Delivery package entity and assignment state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.entities.mixins.event_mixin import DomainEventRecorderMixin
from src.domain.enums.item_status import ItemStatus
from src.domain.events.package_events import PackageCreated, PackageDelivered, PackagePickedUp, PackageRemoved
from src.domain.exceptions import BusinessRuleViolationError, DomainValidationError
from src.domain.services.map import Map
from src.domain.validation import (
    require_optional_positive_int,
    require_positive_finite_float,
    require_positive_int,
)
from src.domain.value_objects.location_code import LocationCode, location_code_or_none

if TYPE_CHECKING:
    from src.domain.entities.customer import Customer
    from src.domain.entities.delivery_route import DeliveryRoute
    from src.domain.events.base import DomainEvent


@dataclass(frozen=True, slots=True)
class DeliveryPackageStateSnapshot:
    """Captured mutable package state for restoring after a failed operation."""

    route: DeliveryRoute | None
    route_id: int | None
    status: ItemStatus
    current_location: LocationCode | None
    expected_arrival: datetime | None


class DeliveryPackage(DomainEventRecorderMixin):
    """Package shipment tracked from pickup to delivery."""

    def __init__(
        self,
        start_location: str | LocationCode,
        end_location: str | LocationCode,
        weight: float,
        customer: Customer,
        package_id: int,
        route_id: int | None = None,
    ) -> None:
        """Create a package shipment.

        Args:
            start_location: Raw or typed pickup location code.
            end_location: Raw or typed delivery location code.
            weight: Package weight in kilograms.
            customer: Owning customer.
            package_id: Stable package identifier.
            route_id: Identifier of the route to which the package is assigned.
                This is used only for partial hydration.

        Raises:
            DomainValidationError: If locations are invalid or equal; an id is
                not a positive integer; or weight is not a positive finite
                number.
        """
        self.start_location = LocationCode(start_location)
        self.end_location = LocationCode(end_location)
        self._package_id = require_positive_int(package_id, "package_id")
        self._validate_locations()
        self._current_location = self.start_location
        self.weight = require_positive_finite_float(weight, "weight")
        self.customer = customer
        self._route = None
        self._route_id = require_optional_positive_int(route_id, "route_id")
        self.expected_arrival = None
        self.status = ItemStatus.TODO

        self._pending_events: list[DomainEvent] = []

    def _validate_locations(self) -> None:
        """Validate start and end locations."""
        if not Map.is_valid_location(self.start_location):
            raise DomainValidationError(f"Invalid start location: {self.start_location}")
        if not Map.is_valid_location(self.end_location):
            raise DomainValidationError(f"Invalid end location: {self.end_location}")
        if self.start_location == self.end_location:
            raise DomainValidationError("Start and end locations must be different.")

    @property
    def package_id(self) -> int:
        """Stable package identifier."""
        return self._package_id

    @property
    def route(self) -> DeliveryRoute | None:
        """Reference to the route, to which the package is assigned, if assigned."""
        return self._route

    @route.setter
    def route(self, value: DeliveryRoute | None) -> None:
        self._route = value
        self._route_id = value.route_id if value is not None else None

    @property
    def route_id(self) -> int | None:
        """The ID of the route, to which the package is assigned, if assigned."""
        return self._route_id

    @property
    def current_location(self) -> LocationCode:
        """Current package location."""
        return self._current_location or self.start_location

    @current_location.setter
    def current_location(self, value: str | LocationCode | None) -> None:
        self._current_location = location_code_or_none(value)

    @classmethod
    def create(
        cls,
        start_location: str | LocationCode,
        end_location: str | LocationCode,
        weight: float,
        customer: Customer,
        package_id: int,
        occurred_at: datetime | None = None,
    ) -> DeliveryPackage:
        """Create a delivery package and record its creation event.

        Unlike direct construction, this factory records a `PackageCreated`
        domain event. Persistence mappers should use the constructor when
        rehydrating existing packages.

        Args:
            start_location: Raw or typed pickup location code.
            end_location: Raw or typed delivery location code.
            weight: Package weight in kilograms.
            customer: Owning customer.
            package_id: Stable package identifier.
            occurred_at: Business time of creation. Defaults to the current time.

        Returns:
            Newly created package with one pending `PackageCreated` event.

        Raises:
            DomainValidationError: If locations are invalid or equal, the
                package id is not positive, or weight is not a positive finite
                number.
        """
        package = cls(
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            customer=customer,
            package_id=package_id,
        )

        package._record_event(
            PackageCreated(
                package_id=package.package_id,
                customer_id=customer.customer_id,
                start_location=package.start_location,
                end_location=package.end_location,
                weight=package.weight,
                initial_status=package.status,
                initial_location=package.current_location,
                expected_arrival=package.expected_arrival,
                occurred_at=occurred_at or datetime.now(),
            )
        )

        return package

    def mark_picked_up(self, *, occurred_at: datetime) -> None:
        """Move an assigned package into transit and record its pickup.

        Args:
            occurred_at: Business time of the pickup event.

        Raises:
            BusinessRuleViolationError: If the package is unassigned or is not
                waiting for pickup.
        """
        route_id = self._require_route_id()

        if self.status is not ItemStatus.TODO:
            raise BusinessRuleViolationError(
                f"Cannot mark package {self.package_id} as picked up because its status is {self.status.value}."
            )

        previous_status = self.status
        previous_location = self.current_location
        self.status = ItemStatus.IN_PROGRESS
        self.current_location = self.start_location

        self._record_event(
            PackagePickedUp(
                package_id=self.package_id,
                route_id=route_id,
                previous_status=previous_status,
                new_status=self.status,
                previous_location=previous_location,
                new_location=self.current_location,
                scheduled_arrival=self.expected_arrival,
                occurred_at=occurred_at,
            )
        )

    def mark_delivered(self, *, occurred_at: datetime) -> None:
        """Complete an in-transit package and record its delivery.

        Args:
            occurred_at: Business time of the delivery event.

        Raises:
            BusinessRuleViolationError: If the package is unassigned or is not
                currently in transit.
        """
        route_id = self._require_route_id()

        if self.status is not ItemStatus.IN_PROGRESS:
            raise BusinessRuleViolationError(
                f"Cannot mark package {self.package_id} as delivered because its status is {self.status.value}."
            )

        previous_status = self.status
        previous_location = self.current_location
        self.status = ItemStatus.DONE
        self.current_location = self.end_location

        self._record_event(
            PackageDelivered(
                package_id=self.package_id,
                route_id=route_id,
                previous_status=previous_status,
                new_status=self.status,
                previous_location=previous_location,
                new_location=self.current_location,
                scheduled_arrival=self.expected_arrival,
                occurred_at=occurred_at,
            )
        )

    def record_removal(
        self,
        *,
        previous_route_id: int | None,
        previous_status: ItemStatus,
        previous_location: LocationCode,
        previous_expected_arrival: datetime | None,
        occurred_at: datetime,
    ) -> None:
        """Record that this package was removed from the system.

        Args:
            previous_route_id: Identifier of the route linked before removal, if any.
            previous_status: Package status before removal-related detachment.
            previous_location: Effective package location before removal.
            previous_expected_arrival: Expected arrival before removal, if scheduled.
            occurred_at: Business time at which removal occurred.
        """
        self._record_event(
            PackageRemoved(
                package_id=self.package_id,
                customer_id=self.customer.customer_id,
                previous_route_id=previous_route_id,
                previous_status=previous_status,
                previous_location=previous_location,
                start_location=self.start_location,
                end_location=self.end_location,
                weight=self.weight,
                previous_expected_arrival=previous_expected_arrival,
                occurred_at=occurred_at,
            )
        )

    def _require_route_id(self) -> int:
        route_id = self.route_id
        if route_id is None:
            raise BusinessRuleViolationError(f"Package {self.package_id} is not assigned to a route.")
        return route_id

    def snapshot_state(self) -> DeliveryPackageStateSnapshot:
        """Capture mutable package state.

        Returns:
            Snapshot that can be passed to `restore_state`.
        """
        return DeliveryPackageStateSnapshot(
            route=self.route,
            route_id=self.route_id,
            status=self.status,
            current_location=self._current_location,
            expected_arrival=self.expected_arrival,
        )

    def restore_state(self, snapshot: DeliveryPackageStateSnapshot) -> None:
        """Restore mutable package state from a prior snapshot.

        Args:
            snapshot: State captured by `snapshot_state`.
        """
        self._route = snapshot.route
        self._route_id = snapshot.route_id
        self.status = snapshot.status
        self._current_location = snapshot.current_location
        self.expected_arrival = snapshot.expected_arrival

    def reset_assignment_state(self) -> None:
        """Clear route-derived state and return the package to the unassigned baseline."""
        self.route = None
        self.expected_arrival = None
        self.status = ItemStatus.TODO
        self.current_location = self.start_location
