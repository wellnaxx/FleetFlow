"""Structural contracts for application command and query handlers."""

from typing import Protocol

from src.application.messaging.command import Command
from src.application.messaging.query import Query


class CommandHandler[C: Command, R](Protocol):
    """Execute one concrete command type and produce its typed result.

    Application use cases and temporary command adapters satisfy this protocol
    structurally and do not need to inherit from it. Registration supplies the
    corresponding ``CommandKey[C, R]`` and is owned by composition rather than
    the executor.
    """

    def execute(self, command: C) -> R:
        """Execute the application operation represented by a command.

        Args:
            command: Typed command containing the operation input.

        Returns:
            Result associated with the command's registered key.

        Raises:
            Exception: Propagates application, domain, persistence, and other
                failures raised while executing the command.
        """
        ...


class QueryHandler[Q: Query, R](Protocol):
    """Execute one concrete query type and produce its typed projection.

    Application use cases and temporary query adapters satisfy this protocol
    structurally. They do not own routing keys or registration; composition
    binds an executor to the matching ``QueryKey[Q, R]`` when constructing the
    query bus.
    """

    def execute(self, query: Q) -> R:
        """Execute the read operation represented by a query.

        Args:
            query: Typed query containing filtering or selection input.

        Returns:
            Projection or result associated with the query's registered key.

        Raises:
            Exception: Propagates application, domain, persistence, and other
                failures raised while executing the query.
        """
        ...
