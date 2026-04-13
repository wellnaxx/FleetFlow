from src.commands.base_command.base_command import BaseCommand


class ViewAllTrucks(BaseCommand):
    def execute(self) -> str:
        return "\n\n".join(truck.info() for truck in self._app_data.view_all_trucks()) or "No trucks."
