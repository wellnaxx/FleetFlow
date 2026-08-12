"""CLI command for changing the current user's password."""

import getpass

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.use_cases.auth.change_password import ChangePasswordUseCase


class AuthChangePassword(EventDrainingCommand[ChangePasswordUseCase]):
    """Run the self-service password-change workflow.

    Usage:
        changepassword
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Prompt for current and replacement passwords.

        Returns:
            Password-change confirmation text.

        Raises:
            PermissionError: If no user is authenticated.
            ValueError: If arguments are supplied or password confirmation
                validation fails.
            AuthenticationError: If the current password is incorrect.
        """
        if self._params:
            raise ValueError("changepassword does not accept arguments.")

        current_password = getpass.getpass("Current password: ")
        new_password = getpass.getpass("New password: ")
        confirmation = getpass.getpass("Confirm new password: ")
        validate_passwords(new_password, confirmation)

        self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute(
                current_password=current_password,
                new_password=new_password,
            ),
        )
        return "Password changed."
