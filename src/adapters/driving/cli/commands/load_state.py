"""CLI command for loading world state."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand


class LoadState(CommandBusCommand):
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
            WorldStateFileNotFoundError: If the requested snapshot is absent.
            WorldStateCorruptionError: If the snapshot is malformed or invalid.
            WorldStatePersistenceError: If reading or applying the snapshot fails.
        """
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.command_bus.dispatch(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path=path),
        )
        return f"Loaded state from {abs_path}"
