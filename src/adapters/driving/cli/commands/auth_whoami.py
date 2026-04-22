from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class AuthWhoAmI(BaseCommand[WhoAmIUseCase]):
    def execute(self) -> str:
        u = self._use_case.execute()
        if not u:
            return "Not logged in."
        return f"{u.name} [{u.role.value}]"

