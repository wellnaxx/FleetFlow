"""CLI command for self-service and manager password changes."""

import getpass

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.domain.enums.auth import Permission


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

        # Manager override (requires ADMIN_USER)
        if target:
            if not self.authz.has(Permission.ADMIN_USER):
                raise PermissionError("Missing permission: ADMIN_USER (manager required).")
            new_pw = getpass.getpass(f"New password for '{target}': ")
            confirm = getpass.getpass("Confirm new password: ")
            if new_pw != confirm:
                raise ValueError("Passwords do not match.")
            if len(new_pw) < 8:
                raise ValueError("Password must be at least 8 characters.")
            self._use_case.execute(target, new_pw)
            return f"Password reset for '{target}'."

        # Self-service (must be logged in)
        if not getattr(self._auth, "current_user", None):
            raise PermissionError("Not logged in.")
        username = getattr(self._auth, "last_username", None)
        if not username:
            # Defensive: ensures we know the canonical login id
            raise RuntimeError("No login username recorded. Please log in again.")

        old_pw = getpass.getpass("Old password: ")
        new_pw = getpass.getpass("New password: ")
        confirm = getpass.getpass("Confirm new password: ")
        if new_pw != confirm:
            raise ValueError("Passwords do not match.")
        if len(new_pw) < 8:
            raise ValueError("Password must be at least 8 characters.")
        if new_pw == old_pw:
            raise ValueError("New password must be different from the old password.")

        self._use_case.execute(username, new_pw, old_password=old_pw)
        return "Password changed."

