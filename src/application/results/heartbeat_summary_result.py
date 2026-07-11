"""Result model for heartbeat reconciliation."""

from dataclasses import dataclass

from src.application.events.base import ApplicationEvent
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True)
class HeartbeatSummary:
    """Summary of entities mutated during heartbeat reconciliation.

    Args:
        mutated_routes: Routes whose runtime state changed.
        mutated_packages: Packages whose runtime state changed.
        mutated_trucks_moved: Trucks whose location or transit target changed.
        mutated_trucks_released: Trucks released from completed routes.
        mutated_trucks_reconciled: Trucks whose route reference was repaired.
        reconciliation_events: Application events describing direct state
            corrections that were not represented by domain lifecycle events.
    """

    mutated_routes: tuple[DeliveryRoute, ...]
    mutated_packages: tuple[DeliveryPackage, ...]
    mutated_trucks_moved: tuple[Truck, ...]
    mutated_trucks_released: tuple[Truck, ...]
    mutated_trucks_reconciled: tuple[Truck, ...] = ()
    reconciliation_events: tuple[ApplicationEvent, ...] = ()

    @property
    def routes_updated(self) -> int:
        """Return the number of routes changed by reconciliation."""
        return len(self.mutated_routes)

    @property
    def packages_updated(self) -> int:
        """Return the number of packages changed by reconciliation."""
        return len(self.mutated_packages)

    @property
    def trucks_moved(self) -> int:
        """Return the number of trucks whose movement state changed."""
        return len(self.mutated_trucks_moved)

    @property
    def trucks_released(self) -> int:
        """Return the number of trucks released from routes."""
        return len(self.mutated_trucks_released)

    @property
    def trucks_reconciled(self) -> int:
        """Return the number of trucks whose route reference was repaired."""
        return len(self.mutated_trucks_reconciled)

    @property
    def state_changed(self) -> bool:
        """Return whether any route, package, or truck state changed."""
        return bool(
            self.mutated_routes
            or self.mutated_packages
            or self.mutated_trucks_moved
            or self.mutated_trucks_released
            or self.mutated_trucks_reconciled
        )

    @property
    def event_recorders(self) -> tuple[DeliveryPackage | DeliveryRoute, ...]:
        """Return each changed domain event recorder once in causal order.

        Route recorders precede package recorders because route lifecycle
        transitions are reconciled before package lifecycle transitions.
        Identity is used instead of equality so distinct entities that compare
        equal are never collapsed.

        Returns:
            Changed package and route recorders, deduplicated by object identity.
        """
        recorders: list[DeliveryPackage | DeliveryRoute] = []
        seen_identities: set[int] = set()

        for recorder in (*self.mutated_routes, *self.mutated_packages):
            recorder_identity = id(recorder)
            if recorder_identity in seen_identities:
                continue

            seen_identities.add(recorder_identity)
            recorders.append(recorder)

        return tuple(recorders)
