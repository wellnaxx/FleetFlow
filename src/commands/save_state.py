from src.commands.base_command.base_command import BaseCommand
class SaveState(BaseCommand):
    """Persist the current application state to a JSON file."""
    def execute(self):
        path = self._params[0] if self._params else "state.json"
        return self._app_data.save(path)
