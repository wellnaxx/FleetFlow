"""CLI command for self-service and manager password changes."""

import getpass

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.change_password import ChangePasswordUseCase


class AuthChangePassword(BaseCommand[ChangePasswordUseCase]):
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
            if new_pw != confirm:
                raise ValueError("Passwords do not match.")
            self._use_case.execute(target, new_pw)
            return f"Password reset for '{target}'."

        old_pw = getpass.getpass("Old password: ")
        new_pw = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        if new_pw != confirm:
            raise ValueError("Passwords do not match.")

        self._use_case.execute_current_user(new_pw, old_password=old_pw)
        return "Password changed."
