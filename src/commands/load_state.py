from src.commands.base_command.base_command import BaseCommand


class LoadState(BaseCommand):
    """Load application state from a JSON file, replacing the current state."""

    mutates_state = True

    def execute(self) -> str:
        path = self._params[0] if self._params else "state.json"
        return self._app_data.load(path)
