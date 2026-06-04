"""CLI command for showing the current authenticated user."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class AuthWhoAmI(BaseCommand[WhoAmIUseCase]):
    """Render the active authentication session."""

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Return the current user's display name and role.

        Returns:
            CLI output for the current session.
        """
        user = self._use_case.execute()
        if not user:
            return "Not logged in."
        return "Not logged in." if not user else f"{user.name} [{user.role.value}]"
