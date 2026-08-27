"""Query-bus-backed CLI command for listing trucks."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.adapters.driving.cli.rendering.truck_info_renderer import render_truck_info
from src.application.queries.trucks.view_all_trucks import VIEW_ALL_TRUCKS, ViewAllTrucksQuery


class ViewAllTrucks(QueryBusCommand):
    """Render the current fleet."""

    def execute(self) -> str:
        """Return truck listing text.

        Returns:
            CLI listing of trucks, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks truck view permission.
        """
        trucks = self.query_bus.dispatch(
            key=VIEW_ALL_TRUCKS,
            query=ViewAllTrucksQuery(),
        )
        return "\n\n".join(render_truck_info(truck) for truck in trucks) or "No trucks."
