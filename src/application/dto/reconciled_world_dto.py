"""DTO for a validated candidate world ready for runtime replacement."""

from dataclasses import dataclass

from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True)
class ReconciledWorld:
    """Fully rebuilt world graph plus prepared truck bindings."""

    customers: dict[int, Customer]
    routes: dict[int, DeliveryRoute]
    packages: dict[int, DeliveryPackage]
    counters: CountersSnapshot
    truck_bindings: list[TruckBinding]
