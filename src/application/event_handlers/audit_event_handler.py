"""Event handler that persists audit records for published events."""

from src.application.eventing.envelope import EventEnvelope
from src.application.eventing.handler import EventHandler
from src.application.models.audit_record import AuditRecordDraft
from src.application.services.audit_mapping.mapper import AuditDescriptorMapper
from src.ports.output.audit_repository import AuditRepositoryPort
from src.shared.event import Event


class AuditEventHandler[E: Event](EventHandler[E]):
    """Convert enveloped events into durable audit record drafts.

    The handler owns the final assembly step for audit persistence. Event-
    specific resource/action/payload fields come from the descriptor mapper;
    universal event and workflow metadata comes from the envelope.
    """

    def __init__(
        self,
        audit_repository: AuditRepositoryPort,
        descriptor_mapper: AuditDescriptorMapper,
    ) -> None:
        """Initialize the handler with audit persistence and mapping services.

        Args:
            audit_repository: Output port used to persist audit drafts.
            descriptor_mapper: Exact-type mapper for event-specific audit data.
        """
        self._audit_repository = audit_repository
        self._descriptor_mapper = descriptor_mapper

    def handle(self, envelope: EventEnvelope[E]) -> None:
        """Persist one audit record for the supplied event envelope.

        Args:
            envelope: Published event plus execution and causality metadata.

        Raises:
            ValueError: If the event type has no audit descriptor mapping.

        Repository failures are intentionally not caught. The dispatcher and
        collector treat audit persistence failure as event publication failure.
        """
        audit_descriptor = self._descriptor_mapper.map(envelope.event)
        draft = AuditRecordDraft(
            event_id=envelope.event.event_id,
            event_version=envelope.event.event_version,
            event_type=type(envelope.event).__name__,
            occurred_at=envelope.event.occurred_at,
            recorded_at=envelope.event.recorded_at,
            envelope_id=envelope.envelope_id,
            correlation_id=envelope.correlation_id,
            causation_id=envelope.causation_id,
            source=envelope.source,
            actor_user_id=envelope.actor.user_id if envelope.actor is not None else None,
            actor_username=envelope.actor.username if envelope.actor is not None else None,
            resource_type=audit_descriptor.resource_type,
            resource_id=audit_descriptor.resource_id,
            action=audit_descriptor.action,
            payload_json=audit_descriptor.payload_json,
        )
        self._audit_repository.add(draft)
