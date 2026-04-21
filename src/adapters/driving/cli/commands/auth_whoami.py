from src.adapters.driving.cli.commands.base_command.base_command import UseCaseCommand
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class AuthWhoAmI(UseCaseCommand[WhoAmIUseCase]):
    def execute(self) -> str:
        u = self._use_case.execute()
        if not u:
            return "Not logged in."
        return f"{u.name} [{u.role.value}]"
