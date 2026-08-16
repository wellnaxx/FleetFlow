"""CLI command for showing the current authenticated user."""

from src.adapters.driving.cli.commands.base_command.query_bus_command import QueryBusCommand
from src.application.queries.auth.who_am_i import WHO_AM_I, WhoAmIQuery


class AuthWhoAmI(QueryBusCommand):
    """Dispatch the principal query and render the active CLI session."""

    skips_heartbeat = True
    autosaves_state = False

    def execute(self) -> str:
        """Return the current user's display name and role.

        Returns:
            Current user's display name and role, or a logged-out message.

        Raises:
            Exception: Propagates query routing and workflow failures.
        """
        user = self.query_bus.dispatch(key=WHO_AM_I, query=WhoAmIQuery())
        if user is None:
            return "Not logged in."
        return f"{user.name} [{user.role.value}]"
