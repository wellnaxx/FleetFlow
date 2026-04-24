from typing import Protocol

from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


class WorldStateRuntimePort(Protocol):
    def replace_world_state(
        self,
        *,
        customers_by_id: dict[int, Customer],
        packages_by_id: dict[int, DeliveryPackage],
        routes_by_id: dict[int, DeliveryRoute],
        counters: CountersSnapshot,
        truck_bindings: list[TruckBinding],
    ) -> None: ...
