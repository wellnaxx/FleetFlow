"""Build and register in-process event publisher subscriptions."""

from typing import NamedTuple

from src.adapters.driven.events.in_process_dispatcher import InProcessEventDispatcher
from src.adapters.driven.events.structured_event_logging_handler import StructuredEventLoggingHandler
from src.application.event_handlers.audit_event_handler import AuditEventHandler
from src.application.eventing.collector import EventCollector
from src.application.services.audit_mapping.mapper import AuditDescriptorMapper
from src.application.services.audit_mapping.registry import build_audit_descriptor_mapper
from src.composition.event_catalog import PUBLISHED_EVENT_TYPES
from src.ports.output.audit_repository import AuditRepositoryPort
from src.ports.output.event_publisher import EventPublisherPort
from src.shared.event import Event


class EventingComponents(NamedTuple):
    """Composed eventing infrastructure exposed to the application runtime.

    Attributes:
        publisher: Event publisher used by the collector to dispatch envelopes.
        collector: Event collector used by driving adapters to publish pending
            events after a workflow completes.
    """

    publisher: EventPublisherPort
    collector: EventCollector


def build_eventing_components(audit_repository: AuditRepositoryPort) -> EventingComponents:
    """Build the in-process event dispatcher, handlers, and collector.

    Args:
        audit_repository: Repository used by the audit handler subscribed to
            every auditable event type.

    Returns:
        Eventing infrastructure with structured logging subscribed to all
        published event types and audit persistence subscribed to auditable
        event types.

    Failure policy:
        Publishing through the returned dispatcher propagates handler failures.
        Audit repository failures therefore become publication failures by
        design.
    """
    dispatcher = InProcessEventDispatcher()
    logging_handler = StructuredEventLoggingHandler()
    descriptor_mapper = build_audit_descriptor_mapper()
    audit_handler = AuditEventHandler[Event](audit_repository, descriptor_mapper)

    register_event_subscriptions(dispatcher, logging_handler, audit_handler, descriptor_mapper)

    return EventingComponents(
        publisher=dispatcher,
        collector=EventCollector(dispatcher),
    )


def register_event_subscriptions(
    dispatcher: InProcessEventDispatcher,
    logging_handler: StructuredEventLoggingHandler,
    audit_handler: AuditEventHandler[Event],
    descriptor_mapper: AuditDescriptorMapper,
) -> None:
    """Register concrete event handlers with the dispatcher.

    Subscriptions are exact event-type matches. The structured logging handler
    is registered before the audit handler, so publication invokes logging
    first and audit persistence second. Handler exceptions are intentionally
    not caught here; the in-process dispatcher propagates them to the publisher.

    Args:
        dispatcher: In-process dispatcher that owns subscription state.
        logging_handler: Observability handler subscribed to every event type
            so event publication can be seen in configured application logs.
        audit_handler: Audit handler subscribed to every mapped event type so
            auditable publication is persisted as normalized audit records.
        descriptor_mapper: Mapper whose registered event types define the
            auditable subscription set independently of logging coverage.
    """
    for event_type in PUBLISHED_EVENT_TYPES:
        dispatcher.subscribe(event_type, logging_handler)

    for event_type in descriptor_mapper.event_types:
        dispatcher.subscribe(event_type, audit_handler)
