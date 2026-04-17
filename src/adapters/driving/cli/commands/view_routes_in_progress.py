from datetime import datetime

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand


class ViewRoutesInProgress(BaseCommand):
    """Return a list of human-friendly strings for routes currently in progress."""

    def execute(self) -> str:
        now = datetime.now()
        active = self._app_data.view_routes_in_progress(now=now)
        if not active:
            return "No routes in progress."

        lines: list[str] = []
        for route, pos in active:
            lines.append(route.info())
            if pos.kind == "IN_TRANSIT":
                lines.append(f"  >> Currently between {pos.from_city} → {pos.to_city}, ETA {pos.next_eta}")
            elif pos.kind == "AT_STOP":
                lines.append(f"  >> Currently at stop: {pos.stop_city}")
            lines.append("")
        return "\n".join(lines)
