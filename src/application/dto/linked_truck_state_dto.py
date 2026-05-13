"""DTOs for truck links restored during snapshot preparation."""

from collections.abc import Mapping
from dataclasses import dataclass

from src.application.dto.candidate_truck_dto import CandidateTruckLink


@dataclass(frozen=True)
class LinkedTruckState:
    """Candidate truck links restored from a world-state snapshot.

    Args:
        trucks_by_route_id: Candidate truck links keyed by assigned route id.
        candidate_trucks_by_id: Candidate truck links keyed by truck vehicle id.
    """

    trucks_by_route_id: Mapping[int, CandidateTruckLink]
    candidate_trucks_by_id: Mapping[int, CandidateTruckLink]
