from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.services.authorization_service import requires
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from src.domain.enums.auth import Permission


class LoadState(BaseCommand[LoadWorldStateUseCase]):
    """Load application state from a JSON file, replacing the current state."""

    mutates_state = True

    @requires(Permission.APP_LOAD_STATE)
    def execute(self) -> str:
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.use_case.execute(path)
        return f"Loaded state from {abs_path}"

