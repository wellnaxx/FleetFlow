"""Build and register in-process event publisher subscriptions."""

from typing import NamedTuple

from src.adapters.driven.events.in_process_dispatcher import InProcessEventDispatcher
from src.adapters.driven.events.structured_event_logging_handler import StructuredEventLoggingHandler
from src.application.event_handlers.audit_event_handler import AuditEventHandler
from src.application.eventing.collector import EventCollector
from src.application.events.auth_events import (
    AuthorizationDenied,
    UserAuthenticated,
    UserLoginRejected,
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
    UserRegistered,
    UserRegistrationRejected,
    UserSessionEnded,
    UserTokensRevoked,
)
from src.application.events.reconciliation_events import (
    PackageStateReconciled,
    RouteStateReconciled,
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)
from src.application.events.startup_events import FleetSeeded
from src.application.events.world_state_events import (
    WorldStateAdvanced,
    WorldStateCorruptionDetected,
    WorldStateExported,
    WorldStateExportFailed,
    WorldStateImported,
    WorldStateImportFailed,
    WorldStateRuntimeSwapped,
    WorldStateSnapshotQuarantined,
    WorldStateStartupRestored,
    WorldStateStartupRestoreFailed,
    WorldStateStartupRestoreSkipped,
)
from src.domain.events.customer_events import CustomerCreated
from src.domain.events.package_events import (
    PackageCreated,
    PackageDelivered,
    PackagePickedUp,
    PackageRemoved,
)
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
)
from src.ports.output.audit_repository import AuditRepositoryPort
from src.ports.output.event_publisher import EventPublisherPort
from src.shared.event import Event

EVENT_TYPES = (
    CustomerCreated,
    PackageCreated,
    PackageRemoved,
    PackagePickedUp,
    PackageDelivered,
    RouteCreated,
    RouteScheduled,
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    TruckAssignedToRoute,
    TruckReleasedFromRoute,
    RouteStarted,
    RouteCompleted,
    RouteRemoved,
    UserRegistered,
    UserRegistrationRejected,
    UserPasswordChanged,
    UserPasswordChangeRejected,
    UserPasswordReset,
    UserPasswordResetRejected,
    UserAuthenticated,
    UserLoginRejected,
    UserSessionEnded,
    UserTokensRevoked,
    AuthorizationDenied,
    FleetSeeded,
    WorldStateExported,
    WorldStateExportFailed,
    WorldStateImported,
    WorldStateImportFailed,
    WorldStateCorruptionDetected,
    WorldStateSnapshotQuarantined,
    WorldStateRuntimeSwapped,
    WorldStateStartupRestored,
    WorldStateStartupRestoreSkipped,
    WorldStateStartupRestoreFailed,
    WorldStateAdvanced,
    RouteStateReconciled,
    PackageStateReconciled,
    TruckPositionReconciled,
    TruckRouteReferenceReconciled,
)


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
        Eventing infrastructure with structured logging and audit persistence
        handlers subscribed to all currently defined event types.

    Failure policy:
        Publishing through the returned dispatcher propagates handler failures.
        Audit repository failures therefore become publication failures by
        design.
    """
    dispatcher = InProcessEventDispatcher()
    logging_handler = StructuredEventLoggingHandler()
    audit_handler = AuditEventHandler[Event](audit_repository)

    register_event_subscriptions(dispatcher, logging_handler, audit_handler)

    return EventingComponents(
        publisher=dispatcher,
        collector=EventCollector(dispatcher),
    )


def register_event_subscriptions(
    dispatcher: InProcessEventDispatcher,
    logging_handler: StructuredEventLoggingHandler,
    audit_handler: AuditEventHandler[Event],
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
        audit_handler: Audit handler subscribed to every event type
            so event publication is persisted as normalized audit records.
    """
    for event_type in EVENT_TYPES:
        dispatcher.subscribe(event_type, audit_handler)
        dispatcher.subscribe(event_type, logging_handler)
