from src.commands.base_command.base_command import BaseCommand


class AuthWhoAmI(BaseCommand):
    def execute(self) -> str:
        u = getattr(self._auth, "current_user", None)
        if not u:
            return "Not logged in."
        return f"{u.name} [{u.role.value}]"
