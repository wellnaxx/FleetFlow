from src.commands.base_command.base_command import BaseCommand


class ViewAllRoutes(BaseCommand):
    def execute(self) -> str:
        routes = self._app_data.view_all_routes()
        return "\n\n".join(r.info() for r in routes) if routes else "No routes available."
