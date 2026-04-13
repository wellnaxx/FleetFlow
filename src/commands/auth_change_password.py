import getpass

from src.commands.base_command.base_command import BaseCommand
from src.models.auth import Permission


class AuthChangePassword(BaseCommand):
    """
    Usage:
      changepassword                # self-service: prompts old/new/confirm
      changepassword <username>     # manager override: prompts new/confirm only
    """

    def execute(self) -> str:
        target = self._params[0].strip().lower() if self._params else None

        # Manager override (requires ADMIN_USER)
        if target:
            if not self._app_data.authz.has(Permission.ADMIN_USER):
                raise PermissionError("Missing permission: ADMIN_USER (manager required).")
            new_pw = getpass.getpass(f"New password for '{target}': ")
            confirm = getpass.getpass("Confirm new password: ")
            if new_pw != confirm:
                raise ValueError("Passwords do not match.")
            if len(new_pw) < 8:
                raise ValueError("Password must be at least 8 characters.")
            self._auth.reset_password(target, new_pw)
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

        self._auth.change_password(username, old_pw, new_pw)
        return "Password changed."
