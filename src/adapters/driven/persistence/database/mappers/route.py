"""Database row mappers for routes."""

from datetime import datetime
from typing import TypedDict

from src.adapters.driven.persistence.database.executor import RowDict
from src.domain.entities.delivery_route import DeliveryRoute
from src.domain.enums.route_status import RouteStatus
from src.domain.value_objects.location_code import LocationCode
from src.shared.validation import require_int, require_optional_datetime, require_optional_int, require_str


class RouteRow(TypedDict):
    route_id: int
    departure_time: datetime | None
    status: str
    truck_vehicle_id: int | None


class RouteStopRow(TypedDict):
    stop_order: int
    location_code: str


def map_route(rows: list[RowDict]) -> DeliveryRoute:
    """Map a database route row and ordered stops to a route entity.

    Args:
        rows: Ordered route query rows. Each row contains the same route fields
            and one route stop.

    Returns:
        Delivery route entity built from the database row and stops.

    Raises:
        KeyError: If a required route or stop column is missing.
        TypeError: If a required route or stop column has an unexpected type.
        ValueError: If the route status is invalid or route construction fails.
    """
    if not rows:
        raise ValueError("Cannot map a route without route rows.")

    typed = as_route_row(rows[0])
    stops = [LocationCode(as_route_stop_row(row)["location_code"]) for row in rows]
    route = DeliveryRoute(
        *stops,
        route_id=typed["route_id"],
        departure_time=typed["departure_time"],
    )
    route.status = RouteStatus(typed["status"])
    return route


def as_route_row(row: RowDict) -> RouteRow:
    """Validate and narrow a generic database row to a route row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed route row with validated field types.

    Raises:
        KeyError: If a required route column is missing.
        TypeError: If a required route column has an unexpected type.
    """
    route_id = require_int(row["route_id"], "route_id")
    departure_time = require_optional_datetime(row["departure_time"], "departure_time")
    status = require_str(row["status"], "status")
    truck_vehicle_id = require_optional_int(row["truck_vehicle_id"], "truck_vehicle_id")

    return RouteRow(
        route_id=route_id,
        departure_time=departure_time,
        status=status,
        truck_vehicle_id=truck_vehicle_id,
    )


def as_route_stop_row(row: RowDict) -> RouteStopRow:
    """Validate and narrow a generic database row to a route stop row.

    Args:
        row: Generic database row returned by the executor.

    Returns:
        Typed route stop row with validated field types.

    Raises:
        KeyError: If a required route stop column is missing.
        TypeError: If a required route stop column has an unexpected type.
    """
    stop_order = require_int(row["stop_order"], "stop_order")
    location_code = require_str(row["location_code"], "location_code")

    return RouteStopRow(
        stop_order=stop_order,
        location_code=location_code,
    )
