"""Input port for dispatching typed application queries."""

from typing import Protocol

from src.application.messaging.query import Query, QueryKey


class QueryBus(Protocol):
    """Dispatch-only application boundary for read-only requests.

    Driving adapters receive this narrow protocol after composition has
    configured the concrete query bus. Registry mutation is intentionally not
    part of the runtime input port.
    """

    def dispatch[Q: Query, R](self, key: QueryKey[Q, R], query: Q) -> R:
        """Dispatch a query to the exact handler registered for its key.

        Args:
            key: Typed routing key binding the concrete query to result ``R``.
            query: Concrete query instance accepted by ``key``.

        Returns:
            Value returned by the registered query handler.

        Raises:
            MessageHandlerNotFoundError: If no handler is registered under the
                supplied key name.
            MessageTypeMismatchError: If the runtime query type does not match
                the key, or the key name belongs to a registration with a
                different query type.
            Exception: Propagates failures raised by the registered handler.
        """
        ...
