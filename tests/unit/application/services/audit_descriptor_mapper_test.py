"""Tests for event-to-audit descriptor mapping."""

import unittest
from datetime import datetime

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.token_revocation_reasons import TokenRevocationReason
from src.application.enums.user_login_rejection_reasons import UserLoginRejectionReason
from src.application.enums.user_password_change_rejection_reasons import UserPasswordChangeRejectionReason
from src.application.enums.user_password_reset_rejection_reasons import UserPasswordResetRejectionReason
from src.application.enums.user_registration_rejection_reasons import UserRegistrationRejectionReason
from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.enums.world_state_startup_skip_reasons import WorldStateStartupSkipReason
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
from src.application.services.audit_descriptor_mapper import map_event_to_audit_descriptor
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.domain.enums.auth import Permission, Role
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.truck_release_reasons import TruckReleaseReason
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
from src.domain.value_objects.location_code import LocationCode
from src.shared.event import Event

NOW = datetime(2025, 1, 1, 12, 0)
LATER = datetime(2025, 1, 1, 18, 0)
COUNTS = WorldStateEntityCounts(customers=1, packages=2, routes=3, trucks=4)


class AuditDescriptorMapperTests(unittest.TestCase):
    """Validate audit descriptors for all currently published event types."""

    def test_maps_all_current_event_types_to_expected_resource_and_action(self) -> None:
        cases = (
            (
                CustomerCreated(customer_id=10, occurred_at=NOW),
                AuditResourceType.CUSTOMER,
                "10",
                AuditAction.CREATED,
            ),
            (
                PackageCreated(
                    package_id=20,
                    customer_id=10,
                    start_location=LocationCode("SYD"),
                    end_location=LocationCode("MEL"),
                    weight=12.5,
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.CREATED,
            ),
            (
                PackageRemoved(package_id=20, customer_id=10, route_id=None, occurred_at=NOW),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.REMOVED,
            ),
            (
                PackagePickedUp(
                    package_id=20,
                    route_id=30,
                    pickup_location=LocationCode("SYD"),
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.PICKED_UP,
            ),
            (
                PackageDelivered(
                    package_id=20,
                    route_id=30,
                    delivery_location=LocationCode("MEL"),
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.DELIVERED,
            ),
            (
                RouteCreated(
                    route_id=30,
                    locations=(LocationCode("SYD"), LocationCode("MEL")),
                    departure_time=NOW,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.CREATED,
            ),
            (
                RouteScheduled(
                    route_id=30,
                    departure_time=NOW,
                    expected_completion_time=LATER,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.SCHEDULED,
            ),
            (
                PackageAssignedToRoute(route_id=30, package_id=20, expected_arrival=LATER, occurred_at=NOW),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.ASSIGNED_TO_ROUTE,
            ),
            (
                PackageDetachedFromRoute(
                    route_id=30,
                    package_id=20,
                    reason=PackageDetachmentReason.ROUTE_REMOVED,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.DETACHED_FROM_ROUTE,
            ),
            (
                TruckAssignedToRoute(route_id=30, truck_id=40, occurred_at=NOW),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.ASSIGNED_TO_TRUCK,
            ),
            (
                TruckReleasedFromRoute(
                    route_id=30,
                    truck_id=40,
                    release_location=LocationCode("MEL"),
                    reason=TruckReleaseReason.ROUTE_COMPLETED,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.RELEASED_TRUCK,
            ),
            (
                RouteStarted(route_id=30, occurred_at=NOW),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.STARTED,
            ),
            (
                RouteCompleted(route_id=30, occurred_at=NOW),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.COMPLETED,
            ),
            (
                RouteRemoved(route_id=30, detached_package_ids=(20,), released_truck_id=40, occurred_at=NOW),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.REMOVED,
            ),
            (
                UserRegistered(user_id=1, username="manager", role=Role.MANAGER, occurred_at=NOW),
                AuditResourceType.USER,
                "1",
                AuditAction.REGISTERED,
            ),
            (
                UserRegistrationRejected(
                    username="bad",
                    reason=UserRegistrationRejectionReason.INVALID_USERNAME,
                    occurred_at=NOW,
                ),
                AuditResourceType.USER,
                None,
                AuditAction.REGISTRATION_REJECTED,
            ),
            (
                UserPasswordChanged(user_id=1, username="manager", occurred_at=NOW),
                AuditResourceType.USER,
                "1",
                AuditAction.PASSWORD_CHANGED,
            ),
            (
                UserPasswordChangeRejected(
                    user_id=None,
                    username=None,
                    reason=UserPasswordChangeRejectionReason.USER_NOT_FOUND,
                    occurred_at=NOW,
                ),
                AuditResourceType.USER,
                None,
                AuditAction.PASSWORD_CHANGE_REJECTED,
            ),
            (
                UserPasswordReset(user_id=1, username="manager", occurred_at=NOW),
                AuditResourceType.USER,
                "1",
                AuditAction.PASSWORD_RESET,
            ),
            (
                UserPasswordResetRejected(
                    user_id=None,
                    username=None,
                    reason=UserPasswordResetRejectionReason.USER_NOT_FOUND,
                    occurred_at=NOW,
                ),
                AuditResourceType.USER,
                None,
                AuditAction.PASSWORD_RESET_REJECTED,
            ),
            (
                UserAuthenticated(user_id=1, username="manager", role=Role.MANAGER, occurred_at=NOW),
                AuditResourceType.USER,
                "1",
                AuditAction.AUTHENTICATED,
            ),
            (
                UserLoginRejected(
                    user_id=None,
                    username="ghost",
                    reason=UserLoginRejectionReason.USER_NOT_FOUND,
                    occurred_at=NOW,
                ),
                AuditResourceType.USER,
                None,
                AuditAction.LOGIN_REJECTED,
            ),
            (
                UserSessionEnded(user_id=1, username="manager", occurred_at=NOW),
                AuditResourceType.USER,
                "1",
                AuditAction.SESSION_ENDED,
            ),
            (
                UserTokensRevoked(
                    user_id=1,
                    username="manager",
                    reason=TokenRevocationReason.USER_LOGOUT,
                    occurred_at=NOW,
                ),
                AuditResourceType.USER,
                "1",
                AuditAction.TOKENS_REVOKED,
            ),
            (
                AuthorizationDenied(
                    user_id=1,
                    username="manager",
                    required_permissions=(Permission.ADMIN_USER,),
                    occurred_at=NOW,
                ),
                AuditResourceType.AUTHORIZATION,
                "1",
                AuditAction.AUTHORIZATION_DENIED,
            ),
            (
                FleetSeeded(truck_count=3, backend="memory", occurred_at=NOW),
                AuditResourceType.FLEET,
                None,
                AuditAction.SEEDED,
            ),
            (
                WorldStateExported(
                    snapshot_path="data/world.json",
                    schema_version=2,
                    entity_counts=COUNTS,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.EXPORTED,
            ),
            (
                WorldStateExportFailed(
                    snapshot_path="data/world.json",
                    schema_version=None,
                    reason=WorldStateFailureReason.PERSISTENCE_FAILURE,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.EXPORT_FAILED,
            ),
            (
                WorldStateImported(
                    snapshot_path="data/world.json",
                    schema_version=2,
                    entity_counts=COUNTS,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.IMPORTED,
            ),
            (
                WorldStateImportFailed(
                    snapshot_path="data/world.json",
                    schema_version=None,
                    reason=WorldStateFailureReason.CORRUPT_SNAPSHOT,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.IMPORT_FAILED,
            ),
            (
                WorldStateCorruptionDetected(
                    snapshot_path="data/world.json",
                    reason=WorldStateCorruptionReason.INVALID_STRUCTURE,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.CORRUPTION_DETECTED,
            ),
            (
                WorldStateSnapshotQuarantined(
                    original_path="data/world.json",
                    quarantined_path="data/quarantine/world.json",
                    reason=WorldStateCorruptionReason.MALFORMED_JSON,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.SNAPSHOT_QUARANTINED,
            ),
            (
                WorldStateRuntimeSwapped(
                    snapshot_path="data/world.json",
                    schema_version=2,
                    entity_counts=COUNTS,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.RUNTIME_SWAPPED,
            ),
            (
                WorldStateStartupRestored(
                    snapshot_path="data/world.json",
                    schema_version=2,
                    entity_counts=COUNTS,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.STARTUP_RESTORED,
            ),
            (
                WorldStateStartupRestoreSkipped(
                    reason=WorldStateStartupSkipReason.NO_SNAPSHOT_FOUND,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.STARTUP_RESTORE_SKIPPED,
            ),
            (
                WorldStateStartupRestoreFailed(
                    snapshot_path="data/world.json",
                    schema_version=None,
                    reason=WorldStateFailureReason.FILE_NOT_FOUND,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.STARTUP_RESTORE_FAILED,
            ),
            (
                WorldStateAdvanced(
                    routes_updated=1,
                    packages_updated=2,
                    trucks_moved=3,
                    trucks_released=4,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.ADVANCED,
            ),
        )

        for event, resource_type, resource_id, action in cases:
            with self.subTest(event=type(event).__name__):
                descriptor = map_event_to_audit_descriptor(event)
                self.assertEqual(descriptor.resource_type, resource_type)
                self.assertEqual(descriptor.resource_id, resource_id)
                self.assertEqual(descriptor.action, action)
                self.assertIsInstance(descriptor.payload_json, dict)

    def test_serializes_package_created_payload(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            PackageCreated(
                package_id=20,
                customer_id=10,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                weight=12.5,
                occurred_at=NOW,
            )
        )

        self.assertEqual(
            descriptor.payload_json,
            {
                "package_id": "20",
                "customer_id": "10",
                "start_location": "SYD",
                "end_location": "MEL",
                "weight": 12.5,
            },
        )

    def test_serializes_route_removed_nullable_truck_id(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            RouteRemoved(route_id=30, detached_package_ids=(20, 21), released_truck_id=None, occurred_at=NOW)
        )

        self.assertEqual(descriptor.payload_json["detached_package_ids"], ["20", "21"])
        self.assertIsNone(descriptor.payload_json["released_truck_id"])

    def test_serializes_authorization_denied_permissions_by_name(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            AuthorizationDenied(
                user_id=None,
                username=None,
                required_permissions=(Permission.ADMIN_USER, Permission.APP_LOAD_STATE),
                occurred_at=NOW,
            )
        )

        self.assertEqual(descriptor.resource_type, AuditResourceType.AUTHORIZATION)
        self.assertIsNone(descriptor.resource_id)
        self.assertEqual(descriptor.payload_json["required_permissions"], ["ADMIN_USER", "APP_LOAD_STATE"])

    def test_serializes_world_state_entity_counts(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            WorldStateExported(
                snapshot_path="data/world.json",
                schema_version=2,
                entity_counts=COUNTS,
                occurred_at=NOW,
            )
        )

        self.assertEqual(
            descriptor.payload_json["entity_counts"],
            {"customers": 1, "packages": 2, "routes": 3, "trucks": 4},
        )

    def test_unsupported_event_type_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported event type: Event"):
            map_event_to_audit_descriptor(Event(occurred_at=NOW))


if __name__ == "__main__":
    unittest.main()
