"""CLI command for administratively resetting a user's password."""

import getpass

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.services.auth_normalization import normalize_username
from src.application.use_cases.auth.reset_password import ResetPasswordUseCase


class AuthResetPassword(EventDrainingCommand[ResetPasswordUseCase]):
    """Run the administrator-only password-reset workflow.

    Usage:
        resetpassword <username>
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Prompt for and reset the target user's password.

        Returns:
            Password-reset confirmation text.

        Raises:
            PermissionError: If the caller lacks user administration access.
            ValueError: If exactly one username is not supplied or password
                confirmation validation fails.
        """
        if len(self._params) != 1:
            raise ValueError("Usage: resetpassword <username>.")

        username = normalize_username(self._params[0])
        if not username:
            raise ValueError("Username must be a non-empty string.")

        new_password = getpass.getpass(f"New password for '{username}': ")
        confirmation = getpass.getpass("Confirm new password: ")
        validate_passwords(new_password, confirmation)

        self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(username=username, new_password=new_password),
        )
        return f"Password reset for '{username}'."
