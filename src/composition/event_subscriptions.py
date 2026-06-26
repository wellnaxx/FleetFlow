"""Build and register in-process event publisher subscriptions."""

from typing import NamedTuple

from src.adapters.driven.events.in_process_dispatcher import InProcessEventDispatcher
from src.adapters.driven.events.structured_event_logging_handler import StructuredEventLoggingHandler
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
from src.ports.output.event_publisher import EventPublisherPort

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


def build_eventing_components() -> EventingComponents:
    """Build the in-process event dispatcher, handlers, and collector.

    Returns:
        Eventing infrastructure with the structured logging handler subscribed
        to all currently defined event types.
    """
    dispatcher = InProcessEventDispatcher()
    logging_handler = StructuredEventLoggingHandler()

    register_event_subscriptions(dispatcher, logging_handler)

    return EventingComponents(
        publisher=dispatcher,
        collector=EventCollector(dispatcher),
    )


def register_event_subscriptions(
    dispatcher: InProcessEventDispatcher,
    logging_handler: StructuredEventLoggingHandler,
) -> None:
    """Register concrete event handlers with the dispatcher.

    Args:
        dispatcher: In-process dispatcher that owns subscription state.
        logging_handler: Observability handler subscribed to every event type
            so event publication can be seen in configured application logs.
    """
    for event_type in EVENT_TYPES:
        dispatcher.subscribe(event_type, logging_handler)
