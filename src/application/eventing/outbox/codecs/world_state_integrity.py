"""World-state snapshot corruption and quarantine outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.world_state_corruption_reasons import WorldStateCorruptionReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.world_state_events import (
    WorldStateCorruptionDetected,
    WorldStateSnapshotQuarantined,
)
from src.shared.json_deserialization import parse_enum_value
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_str

_WORLD_STATE_CORRUPTION_DETECTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(["snapshot_path", "reason"])


class WorldStateCorruptionDetectedEventPayloadCodec(EventPayloadCodec[WorldStateCorruptionDetected]):
    """Encode and decode the version-1 snapshot-corruption detection event.

    Payloads contain exactly snapshot_path and reason. Reasons are persisted
    WorldStateCorruptionReason values describing snapshot defects, not the
    operation-level WorldStateFailureReason classification. No snapshot schema
    version is included. Path text is preserved verbatim; replay does not inspect
    or quarantine the file. Encoding trusts typed event fields, while decoding
    validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateCorruptionDetected]:
        """Return the concrete corruption-detected application event class."""
        return WorldStateCorruptionDetected

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_corruption_detected``."""
        return "world_state_corruption_detected"

    @property
    def event_version(self) -> int:
        """Return version 1 of the corruption-detection payload contract."""
        return 1

    def encode(self, event: WorldStateCorruptionDetected) -> JSONObject:
        """Serialize a detected snapshot defect into a fresh JSON object.

        Args:
            event: Version-1 event with correctly typed corruption fields.

        Returns:
            The unchanged snapshot path and corruption reason string, without
            universal event metadata or snapshot contents.
        """
        return {
            "snapshot_path": event.snapshot_path,
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateCorruptionDetected:
        """Validate a corruption payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly snapshot_path and reason.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event containing a typed WorldStateCorruptionReason and the
            supplied metadata. The payload is neither mutated nor retained.

        Raises:
            TypeError: If the path or reason is not a string, or metadata has
                an invalid runtime type.
            ValueError: If keys are missing or unexpected, the reason is not a
                supported corruption value, or timestamps use the wrong time
                domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_CORRUPTION_DETECTED_PAYLOAD_KEYS)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        reason = parse_enum_value(payload["reason"], "reason", WorldStateCorruptionReason)

        return WorldStateCorruptionDetected(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            reason=reason,
        )


_WORLD_STATE_SNAPSHOT_QUARANTINED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "original_path",
    "quarantined_path",
    "reason",
])


class WorldStateSnapshotQuarantinedEventPayloadCodec(EventPayloadCodec[WorldStateSnapshotQuarantined]):
    """Encode and decode the version-1 snapshot-quarantine event.

    Payloads contain exactly original_path, quarantined_path, and reason. The
    paths describe the source and destination of an already completed move;
    replay preserves their text without accessing or moving files. Reasons use
    WorldStateCorruptionReason values, not operation-level failure categories.
    Encoding trusts typed event fields; decoding validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateSnapshotQuarantined]:
        """Return the concrete snapshot-quarantined application event class."""
        return WorldStateSnapshotQuarantined

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_snapshot_quarantined``."""
        return "world_state_snapshot_quarantined"

    @property
    def event_version(self) -> int:
        """Return version 1 of the snapshot-quarantine payload contract."""
        return 1

    def encode(self, event: WorldStateSnapshotQuarantined) -> JSONObject:
        """Serialize the completed quarantine into a fresh JSON object.

        Args:
            event: Version-1 event with correctly typed paths and reason.

        Returns:
            The unchanged original and quarantined paths and the corruption
            reason string. Universal event metadata is not included.
        """
        return {
            "original_path": event.original_path,
            "quarantined_path": event.quarantined_path,
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateSnapshotQuarantined:
        """Validate a quarantine payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the three version-1 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving both paths and containing a typed
            WorldStateCorruptionReason. Paths are not normalized or checked
            for existence. The payload is neither mutated nor retained.

        Raises:
            TypeError: If either path or the reason is not a string, or metadata
                has an invalid runtime type.
            ValueError: If keys are missing or unexpected, the reason is not a
                supported corruption value, or timestamps use the wrong time
                domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_SNAPSHOT_QUARANTINED_PAYLOAD_KEYS)

        original_path = require_str(payload["original_path"], "original_path")
        quarantined_path = require_str(payload["quarantined_path"], "quarantined_path")
        reason = parse_enum_value(payload["reason"], "reason", WorldStateCorruptionReason)

        return WorldStateSnapshotQuarantined(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            original_path=original_path,
            quarantined_path=quarantined_path,
            reason=reason,
        )
