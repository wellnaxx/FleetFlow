"""CLI command for logging out."""

from src.adapters.driving.cli.commands.base_command.event_draining_command import EventDrainingCommand
from src.application.use_cases.auth.logout import LogoutUseCase


class AuthLogout(EventDrainingCommand[LogoutUseCase]):
    """Revoke tokens and clear the active CLI authentication session."""

    mutates_session = True
    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Log out the current CLI session and return a CLI message.

        Returns:
            Logout confirmation text.
        """
        self._run_and_drain(self._use_case, lambda: self._use_case.execute_current_session())
        return "Logged out."
