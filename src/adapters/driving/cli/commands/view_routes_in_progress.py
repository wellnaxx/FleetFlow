"""CLI command for listing routes currently in progress."""

from datetime import datetime

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.rendering.route_info_renderer import render_route_info
from src.application.use_cases.routes.view_routes_in_progress import ViewRoutesInProgressUseCase
from src.domain.entities.delivery_route import RoutePositionKind


class ViewRoutesInProgress(EventDrainingCommand[ViewRoutesInProgressUseCase]):
    """Return a list of human-friendly strings for routes currently in progress."""

    def execute(self) -> str:
        """Return routes that are currently active.

        Returns:
            CLI listing of active routes, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks in-progress route permission.
        """
        now = datetime.now()
        active = self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(now),
        )
        if not active:
            return "No routes in progress."

        lines: list[str] = []
        for route, pos in active:
            lines.append(render_route_info(route, position=pos))
            if pos.kind == RoutePositionKind.IN_TRANSIT:
                lines.append(f"  >> Currently between {pos.from_city} → {pos.to_city}, ETA {pos.next_eta}")
            elif pos.kind == RoutePositionKind.AT_STOP:
                lines.append(f"  >> Currently at stop: {pos.stop_city}")
            lines.append("")
        return "\n".join(lines)
