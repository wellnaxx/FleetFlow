from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.services.authorization_service import requires
from src.application.use_cases.trucks.view_all_trucks import ViewAllTrucksUseCase
from src.domain.enums.auth import Permission


class ViewAllTrucks(BaseCommand[ViewAllTrucksUseCase]):

    @requires(Permission.TRUCK_VIEW)
    def execute(self) -> str:
        return "\n\n".join(truck.info() for truck in self._use_case.execute()) or "No trucks."

