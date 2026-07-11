"""Tests for event-to-audit descriptor mapping."""

import unittest
from datetime import datetime

from src.application.enums.audit_actions import AuditAction
from src.application.enums.audit_resource_types import AuditResourceType
from src.application.enums.authorization_operations import AuthorizationOperation
from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
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
from src.application.services.audit_descriptor_mapper import map_event_to_audit_descriptor
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.domain.entities.delivery_route import RoutePositionKind
from src.domain.enums.auth import Permission, Role
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.route_status import RouteStatus
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.enums.truck_status import TruckStatus
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
PREVIOUS_COUNTS = WorldStateEntityCounts(customers=0, packages=1, routes=2, trucks=3)


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
                    initial_status=ItemStatus.TODO,
                    initial_location=LocationCode("SYD"),
                    expected_arrival=None,
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.CREATED,
            ),
            (
                PackageRemoved(
                    package_id=20,
                    customer_id=10,
                    previous_route_id=None,
                    previous_status=ItemStatus.TODO,
                    previous_location=LocationCode("SYD"),
                    start_location=LocationCode("SYD"),
                    end_location=LocationCode("MEL"),
                    weight=12.5,
                    previous_expected_arrival=None,
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.REMOVED,
            ),
            (
                PackagePickedUp(
                    package_id=20,
                    route_id=30,
                    previous_status=ItemStatus.TODO,
                    new_status=ItemStatus.IN_PROGRESS,
                    previous_location=LocationCode("SYD"),
                    new_location=LocationCode("SYD"),
                    scheduled_arrival=LATER,
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
                    previous_status=ItemStatus.IN_PROGRESS,
                    new_status=ItemStatus.DONE,
                    previous_location=LocationCode("SYD"),
                    new_location=LocationCode("MEL"),
                    scheduled_arrival=LATER,
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
                    initial_status=RouteStatus.SCHEDULED,
                    expected_completion_time=LATER,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.CREATED,
            ),
            (
                RouteScheduled(
                    route_id=30,
                    previous_status=RouteStatus.PLANNED,
                    new_status=RouteStatus.SCHEDULED,
                    previous_departure_time=None,
                    new_departure_time=NOW,
                    previous_expected_completion_time=None,
                    new_expected_completion_time=LATER,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.SCHEDULED,
            ),
            (
                PackageAssignedToRoute(
                    package_id=20,
                    previous_route_id=None,
                    new_route_id=30,
                    previous_expected_arrival=None,
                    new_expected_arrival=LATER,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.ASSIGNED_TO_ROUTE,
            ),
            (
                PackageDetachedFromRoute(
                    package_id=20,
                    previous_route_id=30,
                    new_route_id=None,
                    previous_status=ItemStatus.IN_PROGRESS,
                    new_status=ItemStatus.TODO,
                    previous_location=LocationCode("SYD"),
                    new_location=LocationCode("SYD"),
                    previous_expected_arrival=LATER,
                    new_expected_arrival=None,
                    reason=PackageDetachmentReason.ROUTE_REMOVED,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.DETACHED_FROM_ROUTE,
            ),
            (
                TruckAssignedToRoute(
                    truck_id=40,
                    previous_route_id=None,
                    new_route_id=30,
                    previous_status=TruckStatus.FREE,
                    new_status=TruckStatus.ON_THE_WAY,
                    previous_location=LocationCode("SYD"),
                    new_location=LocationCode("SYD"),
                    previous_busy_from=None,
                    new_busy_from=NOW,
                    previous_busy_until=None,
                    new_busy_until=LATER,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.ASSIGNED_TO_TRUCK,
            ),
            (
                TruckReleasedFromRoute(
                    truck_id=40,
                    previous_route_id=30,
                    new_route_id=None,
                    previous_status=TruckStatus.ON_THE_WAY,
                    new_status=TruckStatus.FREE,
                    previous_location=LocationCode("SYD"),
                    new_location=LocationCode("MEL"),
                    previous_busy_from=NOW,
                    new_busy_from=None,
                    previous_busy_until=LATER,
                    new_busy_until=None,
                    reason=TruckReleaseReason.ROUTE_COMPLETED,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.RELEASED_TRUCK,
            ),
            (
                RouteStarted(
                    route_id=30,
                    previous_status=RouteStatus.SCHEDULED,
                    new_status=RouteStatus.IN_PROGRESS,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.STARTED,
            ),
            (
                RouteCompleted(
                    route_id=30,
                    previous_status=RouteStatus.IN_PROGRESS,
                    new_status=RouteStatus.COMPLETED,
                    departure_time=NOW,
                    expected_completion_time=LATER,
                    occurred_at=LATER,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.COMPLETED,
            ),
            (
                RouteRemoved(
                    route_id=30,
                    previous_status=RouteStatus.PLANNED,
                    previous_locations=(LocationCode("SYD"), LocationCode("MEL")),
                    previous_departure_time=None,
                    previous_expected_completion_time=None,
                    detached_package_ids=(20,),
                    released_truck_id=40,
                    occurred_at=NOW,
                ),
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
                    attempted_operation=AuthorizationOperation.ROUTE_REMOVE,
                    target_resource_type=AuditResourceType.ROUTE,
                    target_resource_id="30",
                    required_permissions=(Permission.ADMIN_USER,),
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.AUTHORIZATION_DENIED,
            ),
            (
                FleetSeeded(seeded_truck_ids=(1, 2, 3), backend="memory", occurred_at=NOW),
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
                    previous_entity_counts=PREVIOUS_COUNTS,
                    new_entity_counts=COUNTS,
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
                    previous_entity_counts=PREVIOUS_COUNTS,
                    new_entity_counts=COUNTS,
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
                    previous_entity_counts=PREVIOUS_COUNTS,
                    new_entity_counts=COUNTS,
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
                    trucks_reconciled=5,
                    occurred_at=NOW,
                ),
                AuditResourceType.WORLD_STATE,
                None,
                AuditAction.ADVANCED,
            ),
            (
                RouteStateReconciled(
                    route_id=30,
                    previous_status=RouteStatus.IN_PROGRESS,
                    new_status=RouteStatus.SCHEDULED,
                    departure_time=LATER,
                    expected_completion_time=None,
                    reason=RouteReconciliationReason.MISSING_EXPECTED_COMPLETION_TIME,
                    occurred_at=NOW,
                ),
                AuditResourceType.ROUTE,
                "30",
                AuditAction.RECONCILED,
            ),
            (
                PackageStateReconciled(
                    package_id=20,
                    route_id=30,
                    previous_status=ItemStatus.DONE,
                    new_status=ItemStatus.IN_PROGRESS,
                    previous_location=LocationCode("MEL"),
                    new_location=LocationCode("SYD"),
                    previous_expected_arrival=None,
                    new_expected_arrival=LATER,
                    scheduled_pickup_time=NOW,
                    scheduled_delivery_time=LATER,
                    reasons=(PackageReconciliationReason.LIFECYCLE_STATE_INCONSISTENT,),
                    occurred_at=NOW,
                ),
                AuditResourceType.PACKAGE,
                "20",
                AuditAction.RECONCILED,
            ),
            (
                TruckPositionReconciled(
                    truck_id=40,
                    route_id=30,
                    previous_location=None,
                    new_location=LocationCode("SYD"),
                    previous_in_transit_to=None,
                    new_in_transit_to=LocationCode("MEL"),
                    position_kind=RoutePositionKind.IN_TRANSIT,
                    occurred_at=NOW,
                ),
                AuditResourceType.TRUCK,
                "40",
                AuditAction.RECONCILED,
            ),
            (
                TruckRouteReferenceReconciled(
                    truck_id=40,
                    previous_route_id=None,
                    new_route_id=30,
                    occurred_at=NOW,
                ),
                AuditResourceType.TRUCK,
                "40",
                AuditAction.RECONCILED,
            ),
        )

        for event, resource_type, resource_id, action in cases:
            with self.subTest(event=type(event).__name__):
                descriptor = map_event_to_audit_descriptor(event)
                self.assertEqual(descriptor.resource_type, resource_type)
                self.assertEqual(descriptor.resource_id, resource_id)
                self.assertEqual(descriptor.action, action)
                self.assertIsInstance(descriptor.payload_json, dict)
                for key in ("previous_route_id", "new_route_id"):
                    if key in descriptor.payload_json:
                        value = descriptor.payload_json[key]
                        self.assertTrue(value is None or isinstance(value, str))

    def test_serializes_customer_created_without_contact_pii(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            CustomerCreated(
                customer_id=10,
                occurred_at=NOW,
            )
        )

        self.assertEqual(descriptor.payload_json, {"customer_id": "10"})

    def test_serializes_package_created_payload(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            PackageCreated(
                package_id=20,
                customer_id=10,
                start_location=LocationCode("SYD"),
                end_location=LocationCode("MEL"),
                weight=12.5,
                initial_status=ItemStatus.TODO,
                initial_location=LocationCode("SYD"),
                expected_arrival=None,
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
                "initial_status": ItemStatus.TODO.value,
                "initial_location": "SYD",
                "expected_arrival": None,
            },
        )

    def test_serializes_route_removed_nullable_truck_id(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            RouteRemoved(
                route_id=30,
                previous_status=RouteStatus.PLANNED,
                previous_locations=(LocationCode("SYD"), LocationCode("MEL")),
                previous_departure_time=None,
                previous_expected_completion_time=None,
                detached_package_ids=(20, 21),
                released_truck_id=None,
                occurred_at=NOW,
            )
        )

        self.assertEqual(descriptor.payload_json["detached_package_ids"], ["20", "21"])
        self.assertIsNone(descriptor.payload_json["released_truck_id"])

    def test_serializes_route_transition_ids_as_optional_strings(self) -> None:
        assigned = map_event_to_audit_descriptor(
            PackageAssignedToRoute(
                package_id=20,
                previous_route_id=None,
                new_route_id=30,
                previous_expected_arrival=None,
                new_expected_arrival=LATER,
                occurred_at=NOW,
            )
        )
        detached = map_event_to_audit_descriptor(
            PackageDetachedFromRoute(
                package_id=20,
                previous_route_id=30,
                new_route_id=None,
                previous_status=ItemStatus.IN_PROGRESS,
                new_status=ItemStatus.TODO,
                previous_location=LocationCode("SYD"),
                new_location=LocationCode("SYD"),
                previous_expected_arrival=LATER,
                new_expected_arrival=None,
                reason=PackageDetachmentReason.ROUTE_REMOVED,
                occurred_at=NOW,
            )
        )

        self.assertIsNone(assigned.payload_json["previous_route_id"])
        self.assertEqual(assigned.payload_json["new_route_id"], "30")
        self.assertEqual(detached.payload_json["previous_route_id"], "30")
        self.assertIsNone(detached.payload_json["new_route_id"])

    def test_serializes_route_completed_expected_completion_time(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            RouteCompleted(
                route_id=30,
                previous_status=RouteStatus.IN_PROGRESS,
                new_status=RouteStatus.COMPLETED,
                departure_time=NOW,
                expected_completion_time=LATER,
                occurred_at=LATER,
            )
        )

        self.assertEqual(descriptor.payload_json["expected_completion_time"], LATER.isoformat())

    def test_serializes_authorization_denied_permissions_by_name(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            AuthorizationDenied(
                attempted_operation=AuthorizationOperation.WORLD_STATE_IMPORT,
                target_resource_type=AuditResourceType.WORLD_STATE,
                target_resource_id=None,
                required_permissions=(Permission.ADMIN_USER, Permission.APP_LOAD_STATE),
                occurred_at=NOW,
            )
        )

        self.assertEqual(descriptor.resource_type, AuditResourceType.WORLD_STATE)
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

    def test_serializes_package_reconciliation_reasons_by_value(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            PackageStateReconciled(
                package_id=20,
                route_id=None,
                previous_status=ItemStatus.DONE,
                new_status=ItemStatus.TODO,
                previous_location=LocationCode("MEL"),
                new_location=LocationCode("SYD"),
                previous_expected_arrival=LATER,
                new_expected_arrival=None,
                scheduled_pickup_time=None,
                scheduled_delivery_time=None,
                reasons=(
                    PackageReconciliationReason.ROUTE_UNSCHEDULED,
                    PackageReconciliationReason.EXPECTED_ARRIVAL_RECALCULATED,
                ),
                occurred_at=NOW,
            )
        )

        self.assertEqual(descriptor.payload_json["package_id"], "20")
        self.assertIsNone(descriptor.payload_json["route_id"])
        self.assertEqual(
            descriptor.payload_json["reasons"],
            ["route_unscheduled", "expected_arrival_recalculated"],
        )

    def test_preserves_null_truck_reconciliation_positions(self) -> None:
        descriptor = map_event_to_audit_descriptor(
            TruckPositionReconciled(
                truck_id=40,
                route_id=None,
                previous_location=None,
                new_location=None,
                previous_in_transit_to=None,
                new_in_transit_to=None,
                position_kind=RoutePositionKind.UNSCHEDULED,
                occurred_at=NOW,
            )
        )

        self.assertIsNone(descriptor.payload_json["route_id"])
        self.assertIsNone(descriptor.payload_json["previous_location"])
        self.assertIsNone(descriptor.payload_json["new_location"])
        self.assertIsNone(descriptor.payload_json["previous_in_transit_to"])
        self.assertIsNone(descriptor.payload_json["new_in_transit_to"])

    def test_unsupported_event_type_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported event type: Event"):
            map_event_to_audit_descriptor(Event(occurred_at=NOW))


if __name__ == "__main__":
    unittest.main()
