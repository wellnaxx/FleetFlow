"""Command handler for importing world state."""

from src.application.commands.state.load_world import LoadWorldCommand
from src.application.use_cases.state.load_world import LoadWorldStateUseCase


class LoadWorldCommandHandler:
    """Adapt a snapshot-load command to the import workflow."""

    def __init__(self, use_case: LoadWorldStateUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Authorized world-state import workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, command: LoadWorldCommand) -> str:
        """Load world state from the requested path.

        Args:
            command: Snapshot path selected by the driving adapter.

        Returns:
            Resolved path read by the persistence adapter.

        Raises:
            Exception: Propagates authorization, validation, snapshot,
                persistence, and other failures raised by the use case.
        """
        return self._use_case.execute(command.path)
