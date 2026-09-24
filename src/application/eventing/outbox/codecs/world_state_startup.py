"""World-state startup restoration outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.enums.world_state_startup_skip_reasons import WorldStateStartupSkipReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.codecs.entity_counts import decode_entity_counts, encode_entity_counts
from src.application.events.world_state_events import (
    WorldStateStartupRestored,
    WorldStateStartupRestoreFailed,
    WorldStateStartupRestoreSkipped,
)
from src.shared.json_deserialization import parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_optional_positive_int, require_positive_int, require_str

_WORLD_STATE_STARTUP_RESTORED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "snapshot_path",
    "schema_version",
    "previous_customer_count",
    "previous_package_count",
    "previous_route_count",
    "previous_truck_count",
    "new_customer_count",
    "new_package_count",
    "new_route_count",
    "new_truck_count",
])


class WorldStateStartupRestoredEventPayloadCodec(EventPayloadCodec[WorldStateStartupRestored]):
    """Encode and decode the version-2 successful startup-restore event.

    Payloads contain exactly snapshot_path, schema_version, and four
    previous_*_count and four new_*_count fields for customers, packages, routes,
    and trucks. These non-negative snapshots describe the counts before and
    after restoration, not deltas. Counts may increase, decrease, or stay equal.

    The positive snapshot schema_version is independent of event_version.
    Paths are preserved verbatim; decoding neither reads the snapshot nor runs
    startup restoration. Encoding trusts typed event fields, while decoding
    validates serialized values. Version-1 payloads are not upgraded here.
    """

    @property
    def event_class(self) -> type[WorldStateStartupRestored]:
        """Return the concrete startup-restored application event class."""
        return WorldStateStartupRestored

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_startup_restored``."""
        return "world_state_startup_restored"

    @property
    def event_version(self) -> int:
        """Return version 2, whose payload includes before and after counts."""
        return 2

    def encode(self, event: WorldStateStartupRestored) -> JSONObject:
        """Serialize both restoration count snapshots into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed startup-restore fields.

        Returns:
            The unchanged snapshot path, integer schema version, and eight
            flat integer counts. No nested count objects or universal event
            metadata are included.
        """
        return {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            **encode_entity_counts(event.previous_entity_counts, prefix="previous_"),
            **encode_entity_counts(event.new_entity_counts, prefix="new_"),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateStartupRestored:
        """Validate a startup-restore payload and restore its original metadata.

        Args:
            payload: JSON object containing exactly the ten version-2 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with separate previous and new WorldStateEntityCounts
            objects, the original path, and snapshot schema version. The input
            payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans, strings, floats, and None are not valid counts
                or schema versions; snapshot_path must be a string.
            ValueError: If keys are missing or unexpected, schema_version is
                non-positive, any count is negative, or timestamps use the
                wrong time domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_STARTUP_RESTORED_PAYLOAD_KEYS)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_positive_int(payload["schema_version"], "schema_version")
        previous_entity_counts = decode_entity_counts(payload, prefix="previous_")
        new_entity_counts = decode_entity_counts(payload, prefix="new_")

        return WorldStateStartupRestored(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            previous_entity_counts=previous_entity_counts,
            new_entity_counts=new_entity_counts,
        )


_WORLD_STATE_STARTUP_RESTORE_SKIPPED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["reason"])


class WorldStateStartupRestoreSkippedEventPayloadCodec(EventPayloadCodec[WorldStateStartupRestoreSkipped]):
    """Encode and decode the version-1 skipped startup-restore event.

    The payload contains exactly one key, reason, serialized as a
    WorldStateStartupSkipReason value. A skipped restore is distinct from a
    failed operation or detected snapshot corruption; paths, schema versions,
    and entity counts are not part of this event. Encoding trusts typed event
    fields, while decoding validates serialized values without performing
    startup restoration or inspecting the filesystem.
    """

    @property
    def event_class(self) -> type[WorldStateStartupRestoreSkipped]:
        """Return the concrete startup-restore-skipped application event class."""
        return WorldStateStartupRestoreSkipped

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_startup_restore_skipped``."""
        return "world_state_startup_restore_skipped"

    @property
    def event_version(self) -> int:
        """Return version 1 of the skipped-restore payload contract."""
        return 1

    def encode(self, event: WorldStateStartupRestoreSkipped) -> JSONObject:
        """Serialize the skip reason into a fresh JSON object.

        Args:
            event: Version-1 event with a correctly typed startup skip reason.

        Returns:
            A single reason string, without universal event metadata.
        """
        return {"reason": event.reason.value}

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateStartupRestoreSkipped:
        """Validate a skip payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the reason key.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with a typed WorldStateStartupSkipReason and the
            supplied metadata. The payload is neither mutated nor retained.

        Raises:
            TypeError: If reason is not a string, or metadata has an invalid
                runtime type.
            ValueError: If keys are missing or unexpected, reason is not a
                supported skip value, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_STARTUP_RESTORE_SKIPPED_PAYLOAD_KEYS)

        reason = parse_enum_value(payload["reason"], "reason", WorldStateStartupSkipReason)

        return WorldStateStartupRestoreSkipped(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            reason=reason,
        )


_WORLD_STATE_STARTUP_RESTORE_FAILED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "snapshot_path",
    "schema_version",
    "reason",
])


class WorldStateStartupRestoreFailedEventPayloadCodec(EventPayloadCodec[WorldStateStartupRestoreFailed]):
    """Encode and decode the version-1 failed startup-restore event.

    Payloads contain exactly snapshot_path, schema_version, and reason. An
    unknown snapshot schema version is represented by JSON null, not an omitted
    key. Known schema versions are positive integers, independent of the codec
    version. Reasons use operation-level WorldStateFailureReason values, not
    startup skip or snapshot corruption classifications.

    Path text is preserved verbatim; decoding neither accesses the filesystem
    nor retries startup restoration. Encoding trusts typed event fields, while
    decoding validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateStartupRestoreFailed]:
        """Return the concrete startup-restore-failed application event class."""
        return WorldStateStartupRestoreFailed

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_startup_restore_failed``."""
        return "world_state_startup_restore_failed"

    @property
    def event_version(self) -> int:
        """Return the payload contract version, not the snapshot schema version."""
        return 1

    def encode(self, event: WorldStateStartupRestoreFailed) -> JSONObject:
        """Serialize the failed startup restore into a fresh JSON object.

        Args:
            event: Version-1 event with correctly typed failure fields.

        Returns:
            The unchanged path, optional integer snapshot schema version, and
            failure reason string. Universal event metadata is not included.
        """
        return {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateStartupRestoreFailed:
        """Validate a startup failure payload and restore its original metadata.

        Args:
            payload: JSON object containing exactly the three version-1 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with a typed WorldStateFailureReason and the supplied
            metadata. The payload is neither mutated nor retained.

        Raises:
            TypeError: If the path or reason is not a string, schema_version
                is neither None nor an integer (excluding bool), or metadata
                has an invalid runtime type.
            ValueError: If keys are missing or unexpected, a supplied schema
                version is non-positive, the reason is unknown, or timestamps
                use the wrong time domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_STARTUP_RESTORE_FAILED_PAYLOAD_KEYS)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_optional_positive_int(payload["schema_version"], "schema_version")
        reason = parse_enum_value(payload["reason"], "reason", WorldStateFailureReason)

        return WorldStateStartupRestoreFailed(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            reason=reason,
        )
