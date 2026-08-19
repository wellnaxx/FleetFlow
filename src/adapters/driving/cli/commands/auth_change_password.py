"""CLI command for changing the current user's password."""

import getpass

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.commands.auth.change_password import CHANGE_OWN_PASSWORD, ChangeOwnPasswordCommand


class AuthChangePassword(CommandBusCommand):
    """Run the self-service password-change workflow.

    Usage:
        changepassword
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Prompt for passwords and dispatch a self-service change command.

        Returns:
            Password-change confirmation text.

        Raises:
            PermissionError: If no user is authenticated.
            ValueError: If arguments are supplied or password confirmation
                validation fails.
            AuthenticationError: If the current password is incorrect.
            ValidationError: If the account or replacement password is
                invalid.
            NotFoundError: If the authenticated account no longer exists.
            DatabaseError: If password persistence fails.
        """
        if self._params:
            raise ValueError("changepassword does not accept arguments.")

        current_password = getpass.getpass("Current password: ")
        new_password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
        validate_passwords(new_password, confirmation)

        self.command_bus.dispatch(
            key=CHANGE_OWN_PASSWORD,
            command=ChangeOwnPasswordCommand(
                current_password=current_password,
                new_password=new_password,
            ),
        )
        return "Password changed."
