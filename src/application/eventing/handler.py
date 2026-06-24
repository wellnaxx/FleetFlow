from typing import Protocol

from src.application.eventing.envelope import EventEnvelope
from src.shared.event import Event


class EventHandler[E: Event](Protocol):
    """Handle one enveloped domain or application event of type ``E``.

    Implementations consume both the business event and its immutable workflow
    metadata, such as correlation ID, source, and authenticated actor. The
    dispatcher determines when handlers are invoked and how failures are
    handled.
    """

    def handle(self, envelope: EventEnvelope[E]) -> None:
        """Process an event published by the dispatcher.

        Args:
            envelope: Event payload together with execution and causality
                metadata for the workflow that produced it.
        """
        ...
