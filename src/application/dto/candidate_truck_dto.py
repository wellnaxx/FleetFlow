"""DTOs for linking real fleet trucks to candidate restored trucks."""

from dataclasses import dataclass

from src.domain.entities.truck import Truck


@dataclass(frozen=True, slots=True)
class CandidateTruckLink:
    """Pair a live fleet truck with its candidate state during snapshot apply."""

    real_truck: Truck
    candidate_truck: Truck
