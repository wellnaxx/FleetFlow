"""Fleet seeding helpers used by composition roots."""

import logging

from src.domain.entities.truck import Truck
from src.domain.enums.truck_model import TruckModel
from src.domain.services.map import Map
from src.ports.output.truck_repository import TruckRepositoryPort

logger = logging.getLogger(__name__)


def build_default_fleet() -> list[Truck]:
    """Build the fixed default fleet and assign starting locations.

    Returns:
        Default fleet trucks with deterministic starting locations.
    """
    trucks = (
        [Truck(vehicle_id, TruckModel.SCANIA, 42000, 8000) for vehicle_id in range(1001, 1011)]
        + [Truck(vehicle_id, TruckModel.MAN, 37000, 10000) for vehicle_id in range(1011, 1026)]
        + [Truck(vehicle_id, TruckModel.ACTROS, 26000, 13000) for vehicle_id in range(1026, 1041)]
    )
    disperse_trucks(trucks)
    return trucks


def disperse_trucks(trucks: list[Truck]) -> None:
    """Assign trucks to starting locations in deterministic model-group order.

    Args:
        trucks: Fleet trucks whose current locations should be assigned.

    Returns:
        None.
    """
    from collections import defaultdict

    locs = Map.get_locations()
    type_groups: dict[TruckModel, list[Truck]] = defaultdict(list)
    for truck in trucks:
        type_groups[truck.name].append(truck)

    i = 0
    for_type_keys = list(type_groups.keys())
    while any(type_groups.values()):
        for typ in for_type_keys:
            if type_groups[typ]:
                t = type_groups[typ].pop(0)
                t.current_location = locs[i % len(locs)]
                i += 1


def seed_fleet_if_empty(repo: TruckRepositoryPort) -> None:
    """Seed the default fleet when the repository has no trucks.

    Args:
        repo: Truck repository to inspect and seed.

    Returns:
        None.
    """
    existing_fleet = repo.list_fleet()
    if existing_fleet:
        logger.info("Fleet already contains %d trucks; skipping default fleet seed.", len(existing_fleet))
        return

    default_fleet = build_default_fleet()
    logger.info("Seeding default fleet with %d trucks.", len(default_fleet))
    for truck in default_fleet:
        repo.add(truck)
    logger.info("Default fleet seed completed.")
