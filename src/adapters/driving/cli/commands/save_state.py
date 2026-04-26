"""CLI command for saving world state."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.services.authorization_service import requires
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.domain.enums.auth import Permission


class SaveState(BaseCommand[SaveWorldStateUseCase]):
    """Save world state through the CLI authorization boundary.

    Manual save writes external state but does not mutate runtime world state,
    so it must not trigger an additional autosave.
    """

    autosaves_state = False

    @requires(Permission.APP_SAVE_STATE)
    def execute(self) -> str:
        """Persist the current world state to disk.

        The `@requires` decorator on this command is the authorization boundary
        for save-state operations. The underlying use case remains
        authorization-agnostic by design.

        Returns:
            A success message containing the resolved save path.

        Raises:
            PermissionError: If the current user lacks save-state permission.
            ValueError: If the number of parameters is invalid.
        """
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.use_case.execute(path)
        return f"Saved state to {abs_path}"

