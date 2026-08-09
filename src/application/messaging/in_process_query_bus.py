"""Synchronous in-process query registration and dispatch."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import cast

from src.application.messaging.errors import (
    DuplicateMessageHandlerError,
    MessageHandlerNotFoundError,
    MessageTypeMismatchError,
)
from src.application.messaging.handlers import QueryHandler
from src.application.messaging.query import Query, QueryKey


@dataclass(frozen=True, slots=True)
class _QueryRegistration:
    """Runtime-erased query registration stored by routing-key name.

    Attributes:
        query_type: Exact query class accepted by the registration.
        invoke: Type-erased adapter that validates and invokes the concrete
            query handler.
    """

    query_type: type[Query]
    invoke: Callable[[Query], object]


class InProcessQueryBus:
    """Register and synchronously dispatch typed queries in one process.

    Registration is mutable so composition can build the routing table during
    startup. Driving adapters should receive only the dispatch-only
    :class:`~src.ports.input.query_bus.QueryBus` protocol.

    Routing names are the runtime identity of query keys. Each registration
    also retains its exact query type so a newly constructed key cannot
    reuse an occupied name with a different query contract.
    """

    def __init__(self) -> None:
        """Initialize an empty query-handler registry."""
        self._handlers: dict[str, _QueryRegistration] = {}

    def register[Q: Query, R](self, key: QueryKey[Q, R], handler: QueryHandler[Q, R]) -> None:
        """Register one handler under a typed query key.

        Args:
            key: Stable routing name and exact query type to register.
            handler: Concrete handler accepting the key's query type and
                producing its statically associated result.

        Raises:
            DuplicateMessageHandlerError: If ``key.name`` is already
                registered. Existing registrations are never replaced.

        Note:
            The generic signature enforces key/handler compatibility during
            static analysis. Python does not expose those generic parameters
            reliably at runtime, so registration does not inspect handler
            annotations.
        """
        if key.name in self._handlers:
            raise DuplicateMessageHandlerError(f"Handler already registered for {key.name!r}.")

        def invoke(query: Query) -> object:
            if type(query) is not key.query_type:
                raise MessageTypeMismatchError(
                    f"Registration {key.name!r} expects {key.query_type.__name__}, "
                    f"got {type(query).__name__}."
                )
            return handler.handle(cast(Q, query))

        self._handlers[key.name] = _QueryRegistration(
            query_type=key.query_type,
            invoke=invoke,
        )

    def dispatch[Q: Query, R](self, key: QueryKey[Q, R], query: Q) -> R:
        """Synchronously dispatch a query through its registered key.

        Args:
            key: Typed routing key selecting the handler and result type.
            query: Exact query instance declared by ``key``.

        Returns:
            Result returned by the registered query handler.

        Raises:
            MessageTypeMismatchError: If the query's exact runtime type does
                not match ``key.query_type``, or if the registered key name
                belongs to a different query type.
            MessageHandlerNotFoundError: If no handler is registered under
                ``key.name``.
            Exception: Propagates any failure raised by the handler unchanged.
        """
        if type(query) is not key.query_type:
            raise MessageTypeMismatchError(
                f"Query key {key.name!r} expects {key.query_type.__name__}, got {type(query).__name__}."
            )

        try:
            registration = self._handlers[key.name]
        except KeyError as exc:
            raise MessageHandlerNotFoundError(f"No handler registered for query key {key.name!r}.") from exc

        if registration.query_type is not key.query_type:
            raise MessageTypeMismatchError(
                f"Query key {key.name!r} declares {key.query_type.__name__}, but registration "
                f"expects {registration.query_type.__name__}."
            )

        return cast(R, registration.invoke(query))
