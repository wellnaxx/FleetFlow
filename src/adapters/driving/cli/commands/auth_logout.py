"""CLI command for logging out."""

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.application.commands.auth.logout import LOGOUT, LogoutCommand


class AuthLogout(CommandBusCommand):
    """Revoke tokens and clear the active CLI authentication session."""

    mutates_session = True
    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Dispatch logout for the current CLI session.

        Returns:
            Logout confirmation text.

        Raises:
            ValueError: If command arguments are supplied.
            PermissionError: If no valid principal is authenticated.
            DatabaseError: If token revocation persistence fails.
        """
        if self.params:
            raise ValueError("logout does not accept arguments.")

        self.command_bus.dispatch(key=LOGOUT, command=LogoutCommand())
        return "Logged out."
