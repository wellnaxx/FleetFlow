"""Command-bus-backed CLI command for saving world state."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.commands.state.save_world import SAVE_WORLD, SaveWorldCommand


class SaveState(CommandBusCommand):
    """Save world state through the CLI authorization boundary.

    Manual save writes external state but does not mutate runtime world state,
    so it must not trigger an additional autosave.
    """

    autosaves_state = False

    def execute(self) -> str:
        """Persist the current world state to disk.

        Returns:
            A success message containing the resolved save path.

        Raises:
            PermissionError: If the current user lacks save-state permission.
            ValueError: If the number of parameters is invalid.
            WorldStatePersistenceError: If writing the snapshot fails.
        """
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.command_bus.dispatch(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path=path),
        )
        return f"Saved state to {abs_path}"
