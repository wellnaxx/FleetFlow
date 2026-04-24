from dataclasses import dataclass

from src.domain.entities.truck import Truck


@dataclass(frozen=True)
class CandidateTruckLink:
    real_truck: Truck
    candidate_truck: Truck
