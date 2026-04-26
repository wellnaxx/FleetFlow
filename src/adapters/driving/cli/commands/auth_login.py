"""CLI command for logging in."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.login import LoginUseCase


class AuthLogin(BaseCommand[LoginUseCase]):
    """Authenticate a user and update the CLI session."""

    mutates_session = True
    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Prompt for credentials and log in.

        Returns:
            CLI success message for the authenticated user.

        Raises:
            ValueError: If credentials are invalid.
        """
        import getpass

        username = self._params[0] if self._params else input("Username: ").strip()
        password = getpass.getpass("Password: ")
        user = self._use_case.execute(username, password)
        return f"Logged in as {user.name} [{user.role.value}]"
