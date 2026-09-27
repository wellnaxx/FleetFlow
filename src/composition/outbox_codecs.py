"""Explicit composition of current outbox event payload codecs."""

from src.application.eventing.outbox.codecs.auth_passwords import (
    UserPasswordChangedEventPayloadCodec,
    UserPasswordChangeRejectedEventPayloadCodec,
    UserPasswordResetEventPayloadCodec,
    UserPasswordResetRejectedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.auth_registration import (
    UserRegisteredEventPayloadCodec,
    UserRegistrationRejectedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.auth_sessions import (
    UserAuthenticatedEventPayloadCodec,
    UserLoginRejectedEventPayloadCodec,
    UserSessionEndedEventPayloadCodec,
    UserTokensRevokedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.authorization import AuthorizationDeniedEventPayloadCodec
from src.application.eventing.outbox.codecs.customers import CustomerCreatedEventPayloadCodec
from src.application.eventing.outbox.codecs.packages import (
    PackageCreatedEventPayloadCodec,
    PackageDeliveredEventPayloadCodec,
    PackagePickedUpEventPayloadCodec,
    PackageRemovedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.reconciliation import (
    PackageStateReconciledEventPayloadCodec,
    RouteStateReconciledEventPayloadCodec,
    TruckPositionReconciledEventPayloadCodec,
    TruckRouteReferenceReconciledEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.route_lifecycle import (
    RouteCompletedEventPayloadCodec,
    RouteCreatedEventPayloadCodec,
    RouteRemovedEventPayloadCodec,
    RouteScheduledEventPayloadCodec,
    RouteStartedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.route_packages import (
    PackageAssignedToRouteEventPayloadCodec,
    PackageDetachedFromRouteEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.route_trucks import (
    TruckAssignedToRouteEventPayloadCodec,
    TruckReleasedFromRouteEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.startup import FleetSeededEventPayloadCodec
from src.application.eventing.outbox.codecs.world_state_integrity import (
    WorldStateCorruptionDetectedEventPayloadCodec,
    WorldStateSnapshotQuarantinedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.world_state_runtime import (
    WorldStateAdvancedEventPayloadCodec,
    WorldStateRuntimeSwappedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.world_state_startup import (
    WorldStateStartupRestoredEventPayloadCodec,
    WorldStateStartupRestoreFailedEventPayloadCodec,
    WorldStateStartupRestoreSkippedEventPayloadCodec,
)
from src.application.eventing.outbox.codecs.world_state_transfer import (
    WorldStateExportedEventPayloadCodec,
    WorldStateExportFailedEventPayloadCodec,
    WorldStateImportedEventPayloadCodec,
    WorldStateImportFailedEventPayloadCodec,
)
from src.application.eventing.outbox.registry import EventOutboxCodecRegistry
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
from src.domain.events.package_events import PackageCreated, PackageDelivered, PackagePickedUp, PackageRemoved
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


def register_event_payload_codecs(registry: EventOutboxCodecRegistry) -> None:
    """Register one current payload codec for every published event type.

    Args:
        registry: Registry to populate in place. Existing registrations must
            not conflict with these event classes or wire identities.

    Raises:
        DuplicateEventCodecError: If a class or wire identity is registered
            already, including when this function is called twice.
        EventCodecTypeMismatchError: If a codec advertises another event class.
        EventCodecVersionMismatchError: If a codec's version is not current.
        TypeError: If a registration identity has an invalid runtime type.
        ValueError: If a wire name or version is invalid.

    Registration is explicit and ordered like ``PUBLISHED_EVENT_TYPES``.
    Historical decoders are not installed here. Failures propagate immediately;
    registrations completed before a failure remain in the supplied registry.
    """
    registry.register(CustomerCreated, CustomerCreatedEventPayloadCodec())
    registry.register(PackageCreated, PackageCreatedEventPayloadCodec())
    registry.register(PackageRemoved, PackageRemovedEventPayloadCodec())
    registry.register(PackagePickedUp, PackagePickedUpEventPayloadCodec())
    registry.register(PackageDelivered, PackageDeliveredEventPayloadCodec())

    registry.register(RouteCreated, RouteCreatedEventPayloadCodec())
    registry.register(RouteScheduled, RouteScheduledEventPayloadCodec())
    registry.register(PackageAssignedToRoute, PackageAssignedToRouteEventPayloadCodec())
    registry.register(PackageDetachedFromRoute, PackageDetachedFromRouteEventPayloadCodec())
    registry.register(TruckAssignedToRoute, TruckAssignedToRouteEventPayloadCodec())
    registry.register(TruckReleasedFromRoute, TruckReleasedFromRouteEventPayloadCodec())
    registry.register(RouteStarted, RouteStartedEventPayloadCodec())
    registry.register(RouteCompleted, RouteCompletedEventPayloadCodec())
    registry.register(RouteRemoved, RouteRemovedEventPayloadCodec())

    registry.register(UserRegistered, UserRegisteredEventPayloadCodec())
    registry.register(UserRegistrationRejected, UserRegistrationRejectedEventPayloadCodec())
    registry.register(UserPasswordChanged, UserPasswordChangedEventPayloadCodec())
    registry.register(UserPasswordChangeRejected, UserPasswordChangeRejectedEventPayloadCodec())
    registry.register(UserPasswordReset, UserPasswordResetEventPayloadCodec())
    registry.register(UserPasswordResetRejected, UserPasswordResetRejectedEventPayloadCodec())
    registry.register(UserAuthenticated, UserAuthenticatedEventPayloadCodec())
    registry.register(UserLoginRejected, UserLoginRejectedEventPayloadCodec())
    registry.register(UserSessionEnded, UserSessionEndedEventPayloadCodec())
    registry.register(UserTokensRevoked, UserTokensRevokedEventPayloadCodec())
    registry.register(AuthorizationDenied, AuthorizationDeniedEventPayloadCodec())

    registry.register(FleetSeeded, FleetSeededEventPayloadCodec())
    registry.register(WorldStateExported, WorldStateExportedEventPayloadCodec())
    registry.register(WorldStateExportFailed, WorldStateExportFailedEventPayloadCodec())
    registry.register(WorldStateImported, WorldStateImportedEventPayloadCodec())
    registry.register(WorldStateImportFailed, WorldStateImportFailedEventPayloadCodec())
    registry.register(WorldStateCorruptionDetected, WorldStateCorruptionDetectedEventPayloadCodec())
    registry.register(WorldStateSnapshotQuarantined, WorldStateSnapshotQuarantinedEventPayloadCodec())
    registry.register(WorldStateRuntimeSwapped, WorldStateRuntimeSwappedEventPayloadCodec())
    registry.register(WorldStateStartupRestored, WorldStateStartupRestoredEventPayloadCodec())
    registry.register(WorldStateStartupRestoreSkipped, WorldStateStartupRestoreSkippedEventPayloadCodec())
    registry.register(WorldStateStartupRestoreFailed, WorldStateStartupRestoreFailedEventPayloadCodec())
    registry.register(WorldStateAdvanced, WorldStateAdvancedEventPayloadCodec())

    registry.register(RouteStateReconciled, RouteStateReconciledEventPayloadCodec())
    registry.register(PackageStateReconciled, PackageStateReconciledEventPayloadCodec())
    registry.register(TruckPositionReconciled, TruckPositionReconciledEventPayloadCodec())
    registry.register(TruckRouteReferenceReconciled, TruckRouteReferenceReconciledEventPayloadCodec())


def build_event_payload_codec_registry() -> EventOutboxCodecRegistry:
    """Create a fresh registry populated with all current event payload codecs.

    Each call creates independent registry state and codec instances. Nothing
    is cached, and historical decoders are not installed. Registration errors
    propagate unchanged so invalid composition fails during startup rather
    than returning a partially configured registry.

    Returns:
        A registry populated by :func:`register_event_payload_codecs`.

    Raises:
        DuplicateEventCodecError: If configured registrations conflict.
        EventCodecTypeMismatchError: If a codec advertises another event class.
        EventCodecVersionMismatchError: If a codec's version is not current.
        TypeError: If a registration identity has an invalid runtime type.
        ValueError: If a wire name or version is invalid.
    """
    registry = EventOutboxCodecRegistry()
    register_event_payload_codecs(registry)

    return registry
