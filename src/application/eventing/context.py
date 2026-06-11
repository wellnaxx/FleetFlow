"""Explicit execution context used to construct event envelopes."""

from dataclasses import dataclass
from uuid import UUID

from src.application.enums.event_sources import EventSource
from src.application.eventing.envelope import EventActor, EventEnvelope
from src.shared.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class EventContext:
    """Metadata shared by events produced during one workflow.

    Attributes:
        correlation_id: Identifier shared by the complete workflow.
        source: Execution origin that initiated the workflow.
        actor: Authenticated user that initiated the workflow, if any.
        causation_id: Optional identifier of the direct cause of events created
            under this context.
    """

    correlation_id: UUID
    source: EventSource
    actor: EventActor | None = None
    causation_id: UUID | None = None

    def wrap[E: Event](self, event: E) -> EventEnvelope[E]:
        """Wrap an event with this context.

        Args:
            event: Domain or application event to enrich.

        Returns:
            Event envelope containing the event and this workflow metadata.
        """
        return EventEnvelope(
            event=event,
            source=self.source,
            actor=self.actor,
            correlation_id=self.correlation_id,
            causation_id=self.causation_id,
        )
