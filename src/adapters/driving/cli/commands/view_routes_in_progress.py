"""Query-bus-backed CLI command for listing routes currently in progress."""

from datetime import datetime

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.application.queries.routes.view_routes_in_progress import (
    VIEW_ROUTES_IN_PROGRESS,
    ViewRoutesInProgressQuery,
)
from src.domain.entities.delivery_route import RoutePositionKind


class ViewRoutesInProgress(QueryBusCommand):
    """Render routes that are active at the current app-local time."""

    def execute(self) -> str:
        """Dispatch the active-route query and render its results.

        Returns:
            CLI listing of active routes, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks in-progress route permission.
            DatabaseError: If route retrieval fails.
        """
        active = self.query_bus.dispatch(
            key=VIEW_ROUTES_IN_PROGRESS,
            query=ViewRoutesInProgressQuery(now=datetime.now()),
        )
        if not active:
            return "No routes in progress."

        lines: list[str] = []
        for route, position in active:
            lines.append(render_route_info(route, position=position))
            if position.kind == RoutePositionKind.IN_TRANSIT:
                lines.append(
                    f"  >> Currently between {position.from_city} -> {position.to_city}, "
                    f"ETA {position.next_eta}"
                )
            elif position.kind == RoutePositionKind.AT_STOP:
                lines.append(f"  >> Currently at stop: {position.stop_city}")
            lines.append("")

        return "\n".join(lines)
