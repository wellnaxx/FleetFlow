"""Shared base for CLI commands that dispatch application queries."""

from src.adapters.driving.cli.commands.base_command.base_command import BaseCommand
from src.ports.input.query_bus import QueryBus


class QueryBusCommand(BaseCommand[QueryBus]):
    """Expose an injected dispatch-only query bus to a CLI command.

    The inherited constructor accepts raw CLI parameters followed by the
    query bus. This keeps bus injection explicit without requiring every
    query-backed CLI command to repeat the same constructor.
    """

    @property
    def query_bus(self) -> QueryBus:
        """Return the query bus injected by the command factory."""
        return self.use_case
