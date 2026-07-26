"""CLI rendering for point-in-time fleet-overview projections."""

from src.application.results.fleet_overview import (
    ActiveRouteOverview,
    AtStopPosition,
    FleetOverview,
    InTransitPosition,
)


def render_fleet_overview(overview: FleetOverview) -> str:
    """Return a human-readable fleet operations overview.

    Active routes retain the ordering supplied by the query adapter. The
    renderer performs presentation only and does not recalculate scheduling,
    load, deadline, or utilization data.

    Args:
        overview: Point-in-time fleet projection to render.

    Returns:
        Multi-section CLI summary containing aggregate counts and active-route
        details.
    """
    header = f"""Fleet Overview
Generated at: {overview.generated_at:%Y-%m-%d %H:%M:%S}

Packages:
  Total: {overview.packages.by_status.total}
  To do: {overview.packages.by_status.todo}
  In progress: {overview.packages.by_status.in_progress}
  Done: {overview.packages.by_status.done}
  Unassigned: {overview.packages.unassigned}
  Past due: {overview.packages.past_due}

Routes:
  Total: {overview.routes.by_status.total}
  Planned: {overview.routes.by_status.planned}
  Scheduled: {overview.routes.by_status.scheduled}
  In progress: {overview.routes.by_status.in_progress}
  Completed: {overview.routes.by_status.completed}
  Past due: {overview.routes.past_due}

Trucks:
  Total: {overview.trucks.by_status.total}
  Free: {overview.trucks.by_status.free}
  On the way: {overview.trucks.by_status.on_the_way}
  Unknown location: {overview.trucks.unknown_location}

Active Routes ({len(overview.active_routes)}):"""

    active_routes_body = (
        "  None"
        if not overview.active_routes
        else "\n".join(line for route in overview.active_routes for line in _render_active_route(route))
    )

    return f"{header}\n{active_routes_body}"


def _render_active_route(route: ActiveRouteOverview) -> list[str]:
    """Return formatted lines for one active route.

    Args:
        route: Active-route projection to render.

    Returns:
        Indented route details suitable for insertion into the overview.
    """
    truck = (
        "Not assigned"
        if route.truck is None
        else f"{route.truck.truck_id} ({route.capacity_utilization_percent:.1f}% utilized)"
    )

    return [
        f"  Route {route.route_id}: {route.start_location} -> {route.end_location}",
        f"    Status: {route.status.value}",
        f"    Position: {_render_position(route.position)}",
        f"    Packages: {route.assigned_package_count}",
        f"    Maximum segment load: {route.maximum_segment_load:.2f} kg",
        f"    Truck: {truck}",
    ]


def _render_position(position: AtStopPosition | InTransitPosition) -> str:
    """Return a compact active-route position description.

    Args:
        position: At-stop or in-transit route position.

    Returns:
        Current location or segment with its next ETA.
    """
    match position:
        case AtStopPosition(stop_location=stop_location, next_eta=next_eta):
            eta_str = next_eta.strftime("%Y-%m-%d %H:%M") if next_eta is not None else "Final stop"
            return f"At {stop_location}; next ETA: {eta_str}"
        case InTransitPosition(
            from_location=from_location,
            to_location=to_location,
            next_eta=next_eta,
        ):
            return f"{from_location} -> {to_location}; ETA: {next_eta:%Y-%m-%d %H:%M}"
