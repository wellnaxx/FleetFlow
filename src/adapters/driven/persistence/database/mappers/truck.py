"""Database row mappers for trucks."""

from datetime import datetime
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.truck import Truck
from src.domain.enums.truck_status import TruckStatus
from src.domain.value_objects.location_code import LocationCode
from src.shared.validation import (
    require_int,
    require_optional_naive_datetime,
    require_optional_str,
    require_str,
)


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
    vehicle_id = require_int(row["vehicle_id"], "vehicle_id")
    name = require_str(row["name"], "name")
    capacity = require_int(row["capacity"], "capacity")
    max_range = require_int(row["max_range"], "max_range")
    status = require_str(row["status"], "status")
    current_location = require_optional_str(row["current_location"], "current_location")
    busy_from = require_optional_naive_datetime(row["busy_from"], "busy_from")
    busy_until = require_optional_naive_datetime(row["busy_until"], "busy_until")
    in_transit_to = require_optional_str(row["in_transit_to"], "in_transit_to")

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
