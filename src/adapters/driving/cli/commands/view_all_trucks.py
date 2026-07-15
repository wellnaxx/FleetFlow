"""CLI command for listing trucks."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.rendering.truck_info_renderer import render_truck_info
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase


class ViewAllTrucks(EventDrainingCommand[ViewAllTrucksUseCase]):
    """Render the current fleet."""

    def execute(self) -> str:
        """Return truck listing text.

        Returns:
            CLI listing of trucks, or an empty-state message.

        Raises:
            PermissionError: If the caller lacks truck view permission.
        """
        trucks = self._run_and_drain(self._use_case, self._use_case.execute)
        return "\n\n".join(render_truck_info(truck) for truck in trucks) or "No trucks."
