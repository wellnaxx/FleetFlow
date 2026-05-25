"""Database row mappers for trucks."""

from datetime import datetime
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode


class TruckRow(TypedDict):
    vehicle_id: int
    name: str
    capacity: int
    max_range: int
    status: str
    current_location: str | None
    busy_from: datetime | None
    busy_until: datetime | None
    in_transit_to: str | None


def map_truck(row: RowDict) -> Truck:
    """Map a database truck row to a truck entity.

    Args:
        row: Column-name-keyed database row for a truck.

    Returns:
        Truck entity built from the database row.

    Raises:
        KeyError: If a required truck column is missing.
        TypeError: If a required truck column has an unexpected type.
        ValueError: If persisted enum or location values are invalid.
    """
    typed = _as_truck_row(row)
    truck = Truck(
        vehicle_id=typed["vehicle_id"],
        name=typed["name"],
        capacity=typed["capacity"],
        max_range=typed["max_range"],
    )
    truck.status = TruckStatus(typed["status"])
    truck.current_location = (
        LocationCode(typed["current_location"]) if typed["current_location"] is not None else None
    )
    truck.busy_from = typed["busy_from"]
    truck.busy_until = typed["busy_until"]
    truck.in_transit_to = LocationCode(typed["in_transit_to"]) if typed["in_transit_to"] is not None else None
    return truck


def _as_truck_row(row: RowDict) -> TruckRow:
    """Validate and narrow a generic database row to a truck row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed truck row with validated field types.

    Raises:
        KeyError: If a required truck column is missing.
        TypeError: If a required truck column has an unexpected type.
    """
    vehicle_id = row["vehicle_id"]
    name = row["name"]
    capacity = row["capacity"]
    max_range = row["max_range"]
    status = row["status"]
    current_location = row["current_location"]
    busy_from = row["busy_from"]
    busy_until = row["busy_until"]
    in_transit_to = row["in_transit_to"]

    if not isinstance(vehicle_id, int) or isinstance(vehicle_id, bool):
        raise TypeError(f"vehicle_id: expected int, got {type(vehicle_id).__name__}")
    if not isinstance(name, str):
        raise TypeError(f"name: expected str, got {type(name).__name__}")
    if not isinstance(capacity, int) or isinstance(capacity, bool):
        raise TypeError(f"capacity: expected int, got {type(capacity).__name__}")
    if not isinstance(max_range, int) or isinstance(max_range, bool):
        raise TypeError(f"max_range: expected int, got {type(max_range).__name__}")
    if not isinstance(status, str):
        raise TypeError(f"status: expected str, got {type(status).__name__}")
    if current_location is not None and not isinstance(current_location, str):
        raise TypeError(f"current_location: expected str or None, got {type(current_location).__name__}")
    if busy_from is not None and not isinstance(busy_from, datetime):
        raise TypeError(f"busy_from: expected datetime or None, got {type(busy_from).__name__}")
    if busy_until is not None and not isinstance(busy_until, datetime):
        raise TypeError(f"busy_until: expected datetime or None, got {type(busy_until).__name__}")
    if in_transit_to is not None and not isinstance(in_transit_to, str):
        raise TypeError(f"in_transit_to: expected str or None, got {type(in_transit_to).__name__}")

    return TruckRow(
        vehicle_id=vehicle_id,
        name=name,
        capacity=capacity,
        max_range=max_range,
        status=status,
        current_location=current_location,
        busy_from=busy_from,
        busy_until=busy_until,
        in_transit_to=in_transit_to,
    )
