from src.commands.base_command.base_command import BaseCommand


class AuthLogout(BaseCommand):
    mutates_session = True

    def execute(self) -> str:
        self._auth.logout()
        return "Logged out."
