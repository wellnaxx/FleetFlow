"""CLI command for administratively resetting a user's password."""

import getpass

from src.adapters.driving.cli.commands.base_command.command_bus_command import CommandBusCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.commands.auth.reset_password import RESET_USER_PASSWORD, ResetUserPasswordCommand
from src.application.services.auth_normalization import normalize_username


class AuthResetPassword(CommandBusCommand):
    """Run the administrator-only password-reset workflow.

    Usage:
        resetpassword <username>
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Prompt for a replacement password and dispatch an admin reset.

        Returns:
            Password-reset confirmation text.

        Raises:
            PermissionError: If the caller lacks user administration access.
            ValueError: If exactly one username is not supplied or password
                confirmation validation fails.
            ValidationError: If the target or replacement password is invalid.
            NotFoundError: If the target account does not exist.
            DatabaseError: If password persistence fails.
        """
        if len(self.params) != 1:
            raise ValueError("Usage: resetpassword <username>.")

        username = normalize_username(self.params[0])
        if not username:
            raise ValueError("Username must be a non-empty string.")

        new_password = getpass.getpass(f"New password for '{username}': ")
        confirmation = getpass.getpass("Confirm new password: ")
        validate_passwords(new_password, confirmation)

        self.command_bus.dispatch(
            key=RESET_USER_PASSWORD,
            command=ResetUserPasswordCommand(
                username=username,
                new_password=new_password,
            ),
        )
        return f"Password reset for '{username}'."
