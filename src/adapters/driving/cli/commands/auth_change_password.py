"""CLI command for self-service and manager password changes."""

import getpass

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.adapters.driving.cli.commands.validation_helpers import validate_passwords
from src.application.use_cases.auth.change_password import ChangePasswordUseCase


class AuthChangePassword(EventDrainingCommand[ChangePasswordUseCase]):
    """Change the current user's password or reset another user's password.

    Usage:
        changepassword: self-service flow prompting old/new/confirm.
        changepassword <username>: manager override prompting new/confirm.
    """

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Run the password-change flow.

        Returns:
            CLI confirmation text.

        Raises:
            PermissionError: If the caller is not authorized.
            ValueError: If password confirmation or validation fails.
        """
        target = self._params[0].strip().lower() if self._params else None

        if target:
            new_pw = getpass.getpass(f"New password for '{target}': ")
            confirm = getpass.getpass("Confirm new password: ")
            validate_passwords(new_pw, confirm)

            self._run_and_drain(self._use_case, lambda: self._use_case.execute(target, new_pw))
            return f"Password reset for '{target}'."

        old_pw = getpass.getpass("Old password: ")
        new_pw = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        validate_passwords(new_pw, confirm)

        self._run_and_drain(
            self._use_case,
            lambda: self._use_case.execute_current_user(
                new_pw,
                old_password=old_pw,
            ),
        )

        return "Password changed."
