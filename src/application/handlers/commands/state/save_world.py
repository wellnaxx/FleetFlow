"""Command handler for exporting world state."""

from src.application.commands.state.save_world import SaveWorldCommand
from src.application.use_cases.state.save_world import SaveWorldStateUseCase


class SaveWorldCommandHandler:
    """Adapt a snapshot-save command to the export workflow."""

    def __init__(self, use_case: SaveWorldStateUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized world-state export workflow to invoke.
        """
        self._use_case = use_case

    def handle(self, command: SaveWorldCommand) -> str:
        """Save world state to the requested path.

        Args:
            command: Snapshot path selected by the driving adapter.

        Returns:
            Resolved path written by the persistence adapter.

        Raises:
            Exception: Propagates authorization, validation, snapshot,
                persistence, and other failures raised by the use case.
        """
        return self._use_case.execute(command.path)
