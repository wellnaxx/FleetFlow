"""Output port for atomic world-state runtime replacement."""

from collections.abc import Mapping
from typing import Protocol

from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


class WorldStateRuntimePort(Protocol):
    """Port used by snapshot loading to commit a prepared world graph."""

    def replace_world_state(
        self,
        *,
        customers_by_id: Mapping[int, Customer],
        packages_by_id: Mapping[int, DeliveryPackage],
        routes_by_id: Mapping[int, DeliveryRoute],
        counters: CountersSnapshot,
        truck_bindings: list[TruckBinding],
    ) -> None:
        """Replace runtime world state.

        Args:
            customers_by_id: Prepared customer objects keyed by id.
            packages_by_id: Prepared package objects keyed by id.
            routes_by_id: Prepared route objects keyed by id.
            counters: Repository id counters to apply.
            truck_bindings: Prepared live truck state.
        """
        ...
