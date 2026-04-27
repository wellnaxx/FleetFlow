"""DTO for a validated candidate world ready for runtime replacement."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from src.application.dto.truck_binding_dto import TruckBinding
from src.application.dto.world_state_snapshot_dto import CountersSnapshot
from src.domain.entities.customer import Customer
from src.domain.entities.delivery_package import DeliveryPackage
from src.domain.entities.delivery_route import DeliveryRoute


@dataclass(frozen=True)
class ReconciledWorld:
    """Fully rebuilt world graph plus prepared truck bindings.

    The containers are shallow-immutable: callers cannot replace mapping entries
    or append truck bindings after construction. The domain entities inside the
    containers remain mutable because they are the prepared runtime objects.
    """

    customers: Mapping[int, Customer]
    routes: Mapping[int, DeliveryRoute]
    packages: Mapping[int, DeliveryPackage]
    counters: CountersSnapshot
    truck_bindings: tuple[TruckBinding, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "customers", MappingProxyType(dict(self.customers)))
        object.__setattr__(self, "routes", MappingProxyType(dict(self.routes)))
        object.__setattr__(self, "packages", MappingProxyType(dict(self.packages)))
        object.__setattr__(self, "truck_bindings", tuple(self.truck_bindings))
