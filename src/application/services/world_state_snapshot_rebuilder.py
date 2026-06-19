"""Rebuild detached domain objects from world-state snapshots."""

from collections.abc import Callable, Iterable
from types import MappingProxyType

from src.adapters.driven.persistence.json.serialization import dt_from_str
from src.application.dto.rebuilt_world_dto import RebuiltWorld
from src.application.dto.world_state_snapshot_dto import (
    CustomerSnapshot,
    PackageSnapshot,
    RouteSnapshot,
    WorldStateSnapshot,
)
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.exceptions.world_state_errors import WorldStateCorruptionError
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.exceptions import DomainValidationError
from src.domain.value_objects.contact_info import ContactInfo


class WorldStateSnapshotRebuilder:
    """Rebuild detached domain objects from validated snapshot data."""

    def rebuild(self, snapshot: WorldStateSnapshot) -> RebuiltWorld:
        """Rebuild detached customers, packages, and routes from a snapshot.

        Args:
            snapshot: World-state snapshot to rebuild.

        Returns:
            Rebuilt domain objects and counters from the snapshot.

        Raises:
            WorldStateCorruptionError: If package snapshots reference missing
                rebuilt customers or rebuilt entities violate domain invariants.
        """
        world = snapshot.world

        try:
            rebuilt_customers = self._rebuild_customers(world.customers)
            rebuilt_packages = self._rebuild_packages(world.packages, rebuilt_customers)
            rebuilt_routes = self._rebuild_routes(world.routes)
        except KeyError as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVALID_REFERENCES
            ) from exc
        except (TypeError, ValueError, DomainValidationError) as exc:
            raise WorldStateCorruptionError(
                str(exc), reason=WorldStateCorruptionReason.INVARIANT_VIOLATION
            ) from exc

        return RebuiltWorld(
            customers=MappingProxyType(rebuilt_customers),
            packages=MappingProxyType(rebuilt_packages),
            routes=MappingProxyType(rebuilt_routes),
            counters=world.counters,
        )

    @staticmethod
    def _keyed_by[T, K, V](
        items: Iterable[T], *, key: Callable[[T], K], transform: Callable[[T], V]
    ) -> dict[K, V]:
        """Transform items into a dictionary keyed by a selected value.

        Args:
            items: Source items to transform.
            key: Function that returns the dictionary key for an item.
            transform: Function that converts an item into the stored value.

        Returns:
            Dictionary of transformed values keyed by `key`.
        """
        return {key(item): transform(item) for item in items}

    def _rebuild_customers(self, snapshots: tuple[CustomerSnapshot, ...]) -> dict[int, Customer]:
        """Rebuild customer entities from customer snapshots.

        Args:
            snapshots: Customer snapshots to rebuild.

        Returns:
            Rebuilt customers keyed by customer id.

        Raises:
            TypeError: If contact fields contain invalid value types.
            DomainValidationError: If contact fields violate domain validation.
        """
        return self._keyed_by(
            snapshots,
            key=lambda snapshot: snapshot.customer_id,
            transform=lambda snapshot: Customer(
                customer_id=snapshot.customer_id,
                contact=ContactInfo(name=snapshot.name, email=snapshot.email, phone_number=snapshot.phone),
            ),
        )

    def _rebuild_packages(
        self, snapshots: tuple[PackageSnapshot, ...], rebuilt_customers: dict[int, Customer]
    ) -> dict[int, DeliveryPackage]:
        """Rebuild package entities and restore customer package links.

        Args:
            snapshots: Package snapshots to rebuild.
            rebuilt_customers: Rebuilt customers keyed by customer id.

        Returns:
            Rebuilt packages keyed by package id.

        Raises:
            KeyError: If a package references a missing customer.
            TypeError: If package fields contain invalid value types.
            DomainValidationError: If package fields violate domain validation.
        """
        rebuilt_packages: dict[int, DeliveryPackage] = {}

        for snapshot in snapshots:
            customer = rebuilt_customers[snapshot.customer_id]
            package = DeliveryPackage(
                package_id=snapshot.package_id,
                start_location=snapshot.start,
                end_location=snapshot.end,
                weight=snapshot.weight,
                customer=customer,
            )
            rebuilt_packages[snapshot.package_id] = package
            customer.add_package(package)

        return rebuilt_packages

    def _rebuild_routes(self, snapshots: tuple[RouteSnapshot, ...]) -> dict[int, DeliveryRoute]:
        """Rebuild route entities from route snapshots.

        Args:
            snapshots: Route snapshots to rebuild.

        Returns:
            Rebuilt routes keyed by route id.

        Raises:
            TypeError: If route fields contain invalid value types.
            ValueError: If departure time serialization is invalid.
            DomainValidationError: If route fields violate domain validation.
        """
        return self._keyed_by(
            snapshots,
            key=lambda snapshot: snapshot.route_id,
            transform=lambda snapshot: DeliveryRoute(
                *snapshot.locations,
                departure_time=dt_from_str(snapshot.departure_time),
                route_id=snapshot.route_id,
            ),
        )
