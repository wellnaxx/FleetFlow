"""Output port for publishing enveloped events beyond application workflows."""

from typing import Protocol

from src.application.eventing.envelope import EventEnvelope
from src.shared.event import Event


class EventPublisherPort(Protocol):
    """Publish enveloped domain and application events.

    Publishers receive fully enriched envelopes rather than raw events. They
    do not create workflow metadata or decide which events should be emitted;
    those responsibilities belong to event draining and context enrichment.
    Delivery, retry, and handler-failure policy are defined by the concrete
    publisher implementation. ``EventEnvelope`` is covariant, allowing this
    port to publish envelopes containing any concrete ``Event`` subtype.
    """

    def publish(self, envelope: EventEnvelope[Event]) -> None:
        """Publish one event envelope.

        Args:
            envelope: Event payload together with immutable execution and
                causality metadata.
        """
        ...

    def publish_all(self, envelopes: tuple[EventEnvelope[Event], ...]) -> None:
        """Publish a batch of event envelopes.

        Args:
            envelopes: Envelopes collected from one completed workflow.
        """
        ...
