"""Synchronous in-process implementation of the event publisher output port."""

from collections import defaultdict
from typing import cast

from src.application.eventing.envelope import EventEnvelope
from src.application.eventing.handler import EventHandler
from src.ports.output.event_publisher import EventPublisherPort
from src.shared.event import Event


class InProcessEventDispatcher(EventPublisherPort):
    """Synchronously dispatch envelopes to handlers in the current process.

    Handlers are matched by the concrete type of ``envelope.event``. Handler
    registration order is preserved, and exceptions raised by a handler
    propagate to the publisher. This adapter provides no persistence, retry,
    or cross-process delivery guarantees.

    The handler registry is intentionally type-erased internally. Each
    ``subscribe`` call establishes the runtime invariant that handlers stored
    under ``type[E]`` accept envelopes containing ``E``. Python cannot express
    that dependent key-value relationship in one dictionary, so ``publish``
    recovers it with one localized cast after exact-type lookup.
    """

    def __init__(self) -> None:
        """Initialize an empty exact-event-type handler registry."""
        # Each value is really list[EventHandler[E]] for the E in its key.
        # Python cannot express that dependent/existential relationship.
        self._handlers: dict[type[Event], list[object]] = defaultdict(list)

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Register a handler for events of one exact concrete type.

        Args:
            event_type: Concrete domain or application event type to handle.
            handler: Handler invoked when an envelope contains that event type.
        """
        self._handlers[event_type].append(handler)

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        """Synchronously publish one envelope to its matching handlers.

        Args:
            envelope: Enriched event to route by its concrete event type.

        Raises:
            Exception: Propagates any exception raised by a registered handler.
        """
        for erased_handler in tuple(self._handlers.get(type(envelope.event), ())):
            # `subscribe()` associated this handler's hidden E with `event_type`.
            # Exact-type lookup restores that runtime invariant; the registry remains type-erased.
            handler = cast(EventHandler[Event], erased_handler)
            handler.handle(envelope)

    def publish_all(self, envelopes: tuple[EventEnvelope[Event], ...]) -> None:
        """Publish envelopes sequentially in their supplied order.

        Args:
            envelopes: Envelopes from one completed workflow.

        Raises:
            Exception: Propagates any exception raised while publishing an
                envelope; subsequent envelopes are not dispatched.
        """
        for envelope in envelopes:
            self.publish(envelope)
