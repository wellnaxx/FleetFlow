"""Delivery package entity and assignment state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING

from src.domain.entities.mixins.event_mixin import EventRecorderMixin
from src.domain.enums.item_status import ItemStatus
from src.domain.events.package_events import PackageCreated, PackageDelivered, PackagePickedUp
from src.domain.exceptions import BusinessRuleViolationError, DomainValidationError
from src.domain.services.map import Map
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


class DeliveryPackage(EventRecorderMixin):
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
            DomainValidationError: If locations are invalid, equal, or the weight is not
                positive, or route_id is a boolean or negative.
        """
        self.start_location = LocationCode(start_location)
        self.end_location = LocationCode(end_location)
        self._package_id = package_id
        self._validate_locations()
        self._validate_weight(float(weight))
        self._current_location = self.start_location
        self.weight = weight
        self.customer = customer
        self._route = None
        self._route_id = self._validate_route_id(route_id)
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

    def _validate_weight(self, weight: float) -> None:
        """Validate the weight of the package."""
        if weight <= 0:
            raise DomainValidationError("Weight must be positive.")

    def _validate_route_id(self, route_id: int | None) -> int | None:
        """Validate the route ID."""
        if route_id is not None and (isinstance(route_id, bool) or route_id < 1):
            raise DomainValidationError("Route ID must be a positive integer.")
        return route_id

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
            DomainValidationError: If locations are invalid, equal, or the weight is not positive.
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
                package_id=package_id,
                customer_id=customer.customer_id,
                start_location=package.start_location,
                end_location=package.end_location,
                weight=weight,
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

        self.status = ItemStatus.IN_PROGRESS
        self.current_location = self.start_location

        self._record_event(
            PackagePickedUp(
                package_id=self.package_id,
                route_id=route_id,
                pickup_location=self.start_location,
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

        self.status = ItemStatus.DONE
        self.current_location = self.end_location
        self._record_event(
            PackageDelivered(
                package_id=self.package_id,
                route_id=route_id,
                delivery_location=self.end_location,
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

    def info(self) -> str:
        """Return a human-readable description of the package.

        Returns:
            Multi-line package summary for CLI display.
        """
        contact_info = (
            f"{self.customer.name} ({self.customer.contact.display_email()}, "
            f"{self.customer.contact.display_phone()})"
        )
        route_str = self.route_id if self.route_id else "Not assigned"
        arrival_str = (
            self.expected_arrival.strftime("%Y-%m-%d %H:%M") if self.expected_arrival else "Not assigned"
        )
        return (
            f"Package {self.package_id}: "
            f"{self.start_location} -> {self.end_location}, {self.weight:.1f}kg\n"
            f"Customer: {contact_info}\n"
            f"Assigned route: {route_str}\n"
            f"Expected arrival: {arrival_str}"
        )
