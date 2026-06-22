"""CLI rendering for delivery-route summaries."""

from src.domain.entities.delivery_route import DeliveryRoute, RoutePosition, RoutePositionKind


def render_route_info(route: DeliveryRoute, *, position: RoutePosition | None = None) -> str:
    """Return a human-readable route summary.

    Args:
        route: Route to render.
        position: Precomputed route position to display. When omitted, the
            renderer computes the current position.

    Returns:
        Multi-line route description for CLI display.
    """
    lines: list[str] = [
        f"Route ID: {route.route_id}",
        f"Truck ID: {route.truck.vehicle_id if route.truck else 'Not assigned'}",
        f"Start: {route.start_location}",
        f"End: {route.end_location}",
        (
            f"Departure: {route.departure_time.strftime('%Y-%m-%d %H:%M')}"
            if route.departure_time
            else "Departure: (unscheduled)"
        ),
        f"Total Distance: {route.total_distance_km} km",
        "Stops:" if route.departure_time else "Status: PLANNED (unscheduled)",
        *(
            [
                (f"  - {city} @ {route.arrival_time_at(city).strftime('%Y-%m-%d %H:%M')}")
                for city in route.locations
            ]
            if route.departure_time
            else []
        ),
        _get_status_info(route, position=position),
    ]

    lines.append(f"Assigned weight: {route.total_assigned_weight():.2f} kg")

    return "\n".join(lines)

def _get_status_info(route: DeliveryRoute, *, position: RoutePosition | None) -> str:
    pos = route.current_position() if position is None else position
    if pos.kind == RoutePositionKind.BEFORE_START:
        eta_str = pos.next_eta.strftime("%Y-%m-%d %H:%M") if pos.next_eta else "N/A"
        return f"Status: BEFORE_START (next {pos.stop_city} @ {eta_str})"
    if pos.kind == RoutePositionKind.AT_STOP:
        return f"Status: AT_STOP ({pos.stop_city})"
    if pos.kind == RoutePositionKind.IN_TRANSIT:
        eta_str = pos.next_eta.strftime("%Y-%m-%d %H:%M") if pos.next_eta else "N/A"
        return f"Status: IN_TRANSIT ({pos.from_city} -> {pos.to_city}), ETA {eta_str}"
    return "Status: AFTER_END"
