"""DTOs for detached domain objects rebuilt from world-state snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass

from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True)
class RebuiltWorld:
    """Detached domain graph rebuilt from a world-state snapshot.

    Args:
        customers: Rebuilt customers keyed by customer id.
        packages: Rebuilt packages keyed by package id.
        routes: Rebuilt routes keyed by route id.
        counters: Repository id counters from the snapshot.
    """

    customers: Mapping[int, Customer]
    packages: Mapping[int, DeliveryPackage]
    routes: Mapping[int, DeliveryRoute]
    counters: CountersSnapshot
