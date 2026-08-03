"""Structural contracts for application command and query handlers."""

from typing import Protocol

from src.application.messaging.command import Command
from src.application.messaging.query import Query


class CommandHandler[C: Command, R](Protocol):
    """Handle one concrete command type and produce its typed result.

    Concrete handlers satisfy this protocol structurally and do not need to
    inherit from it. Handler registration supplies the corresponding
    ``CommandKey[C, R]`` and is owned by composition rather than the handler.
    """

    def handle(self, command: C) -> R:
        """Execute the application operation represented by a command.

        Args:
            command: Typed command containing the operation input.

        Returns:
            Result associated with the command's registered key.

        Raises:
            Exception: Propagates application, domain, persistence, and other
                failures raised while handling the command.
        """
        ...


class QueryHandler[Q: Query, R](Protocol):
    """Handle one concrete query type and produce its typed projection.

    Concrete handlers satisfy this protocol structurally. They do not own
    routing keys or registration; composition binds a handler to the matching
    ``QueryKey[Q, R]`` when constructing the query bus.
    """

    def handle(self, query: Q) -> R:
        """Execute the read operation represented by a query.

        Args:
            query: Typed query containing filtering or selection input.

        Returns:
            Projection or result associated with the query's registered key.

        Raises:
            Exception: Propagates application, domain, persistence, and other
                failures raised while handling the query.
        """
        ...
