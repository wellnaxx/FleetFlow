from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.login import LoginUseCase


class AuthLogin(BaseCommand[LoginUseCase]):
    mutates_session = True

    def execute(self) -> str:
        import getpass

        username = self._params[0] if self._params else input("Username: ").strip()
        password = getpass.getpass("Password: ")
        user = self._use_case.execute(username, password)
        return f"Logged in as {user.name} [{user.role.value}]"

