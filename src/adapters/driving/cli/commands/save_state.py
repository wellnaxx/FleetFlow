from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_params_count
from src.application.services.authorization_service import requires
from src.application.use_cases.state.save_world import SaveWorldStateUseCase
from src.domain.enums.auth import Permission


class SaveState(UseCaseCommand[SaveWorldStateUseCase]):
    @requires(Permission.APP_SAVE_STATE)
    def execute(self) -> str:
        validate_params_count(self.params, 0, 1)
        path = self.params[0] if self.params else "state.json"
        abs_path = self.use_case.execute(path)
        return f"Saved state to {abs_path}"
