"""CLI command for loading world state."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.use_cases.state.load_world import LoadWorldStateUseCase


class LoadState(BaseCommand[LoadWorldStateUseCase]):
    """Load world state through the CLI authorization boundary."""

    mutates_state = True
    autosaves_state = False
    skips_heartbeat = True

    def execute(self) -> str:
        """Replace runtime state from a persisted snapshot.

        Returns:
            A success message containing the resolved load path.

        Raises:
            PermissionError: If the current user lacks load-state permission.
            ValueError: If the number of parameters is invalid.
        """
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.use_case.execute(path)
        return f"Loaded state from {abs_path}"
