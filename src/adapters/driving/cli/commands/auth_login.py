"""CLI command for logging in."""

import getpass

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.application.commands.auth.login import LOGIN, LoginCommand


class AuthLogin(CommandBusCommand):
    """Authenticate a user and update the CLI session."""

    mutates_session = True
    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Collect credentials and dispatch a login command.

        Returns:
            CLI success message for the authenticated user.

        Raises:
            ValueError: If more than one username argument is supplied.
            AuthenticationError: If the credentials are rejected.
            ValidationError: If persisted account data is invalid.
            DatabaseError: If account retrieval or persistence fails.
        """
        if len(self.params) > 1:
            raise ValueError("login accepts at most one username argument.")

        username = self.params[0].strip() if self.params else input("Username: ").strip()
        password = getpass.getpass("Password: ")
        result = self.command_bus.dispatch(
            key=LOGIN,
            command=LoginCommand(
                username=username,
                password=password,
            ),
        )
        return f"Logged in as {result.principal.name} [{result.principal.role.value}]"
