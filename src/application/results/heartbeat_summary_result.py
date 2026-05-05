"""Result model for heartbeat reconciliation."""

from dataclasses import dataclass

from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class HeartbeatSummary:
    """Summary of entities mutated during heartbeat reconciliation.

    Args:
        mutated_routes: Routes whose runtime state changed.
        mutated_packages: Packages whose runtime state changed.
        mutated_trucks_moved: Trucks whose location or transit target changed.
        mutated_trucks_released: Trucks released from completed routes.
    """

    mutated_routes: tuple[DeliveryRoute, ...]
    mutated_packages: tuple[DeliveryPackage, ...]
    mutated_trucks_moved: tuple[Truck, ...]
    mutated_trucks_released: tuple[Truck, ...]

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
    def state_changed(self) -> bool:
        """Return whether any route, package, or truck state changed."""
        return bool(
            self.mutated_routes
            or self.mutated_packages
            or self.mutated_trucks_moved
            or self.mutated_trucks_released
        )
