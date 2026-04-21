from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.use_cases.auth.logout import LogoutUseCase


class AuthLogout(UseCaseCommand[LogoutUseCase]):
    mutates_session = True

    def execute(self) -> str:
        self._use_case.execute()
        return "Logged out."
