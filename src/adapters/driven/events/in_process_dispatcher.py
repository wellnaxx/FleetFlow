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
    """

    def __init__(self) -> None:
        """Initialize an empty concrete-event-type handler registry."""
        self._handlers: dict[type[Event], list[EventHandler[Event]]] = defaultdict(list)

    def subscribe[E: Event](self, event_type: type[E], handler: EventHandler[E]) -> None:
        """Register a handler for events of one exact concrete type.

        Args:
            event_type: Concrete domain or application event type to handle.
            handler: Handler invoked when an envelope contains that event type.
        """
        # The registry is an existential map: its key preserves the hidden E
        # associated with each typed handler until exact-type dispatch.
        self._handlers[event_type].append(cast(EventHandler[Event], handler))

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        """Synchronously publish one envelope to its matching handlers.

        Args:
            envelope: Enriched event to route by its concrete event type.

        Raises:
            Exception: Propagates any exception raised by a registered handler.
        """
        for handler in tuple(self._handlers.get(type(envelope.event), ())):
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
