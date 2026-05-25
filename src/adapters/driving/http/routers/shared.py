from src.adapters.driving.http.schemas.trucks import TruckResponse
from src.domain.entities.truck import Truck


def truck_response(truck: Truck) -> TruckResponse:
    """Convert a Truck entity to a TruckResponse model.

    Args:
        truck: Truck entity to convert.

    Returns:
        HTTP response model representing the truck.
    """
    return TruckResponse(
        vehicle_id=truck.vehicle_id,
        name=str(truck.name),
        capacity=truck.capacity,
        max_range=truck.max_range,
        status=truck.status,
        current_location=str(truck.current_location) if truck.current_location is not None else None,
        route_id=truck.route.route_id if truck.route is not None else None,
        busy_from=truck.busy_from,
        busy_until=truck.busy_until,
        in_transit_to=str(truck.in_transit_to) if truck.in_transit_to is not None else None,
    )
