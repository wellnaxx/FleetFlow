from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.logout import LogoutUseCase


class AuthLogout(BaseCommand[LogoutUseCase]):
    mutates_session = True
    skips_heartbeat = True

    def execute(self) -> str:
        self._use_case.execute()
        return "Logged out."

