"""Event handler that writes published events to the application log."""

import logging

from src.application.eventing.envelope import EventEnvelope
from src.application.eventing.handler import EventHandler
from src.shared.event import Event

logger = logging.getLogger(__name__)


class StructuredEventLoggingHandler(EventHandler[Event]):
    """Log published event envelopes for operational observability.

    This handler does not provide durable audit storage. It is a lightweight
    infrastructure adapter for proving and observing the event publication
    pipeline through the configured application logger.
    """

    def handle(self, envelope: EventEnvelope[Event]) -> None:
        """Log one published event envelope.

        Args:
            envelope: Event payload and immutable workflow metadata to log.
        """
        event = envelope.event
        actor = envelope.actor

        logger.info(
            "Event published: event_type=%s event_id=%s occurred_at=%s recorded_at=%s "
            "envelope_id=%s correlation_id=%s causation_id=%s source=%s "
            "actor_user_id=%s actor_username=%s",
            type(event).__name__,
            event.event_id,
            event.occurred_at.isoformat(),
            event.recorded_at.isoformat(),
            envelope.envelope_id,
            envelope.correlation_id,
            envelope.causation_id,
            envelope.source.value,
            actor.user_id if actor else None,
            actor.username if actor else None,
        )
