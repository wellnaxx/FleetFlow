"""CLI rendering for truck summaries."""

from src.domain.entities.truck import Truck


def render_truck_info(truck: Truck) -> str:
    """Return a human-readable truck summary.

    Args:
        truck: Fleet truck to render.

    Returns:
        Multi-line truck summary for CLI display.
    """
    return (
        f"Vehicle ID: {truck.vehicle_id}\n"
        f"Name: {truck.name}\n"
        f"Capacity: {truck.capacity}\n"
        f"Max range: {truck.max_range}\n"
        f"Status: {truck.status}\n"
        f"Location: {truck.current_location or 'Unknown'}"
    )
