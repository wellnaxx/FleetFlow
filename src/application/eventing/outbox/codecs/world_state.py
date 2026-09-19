"""Outbox payload codecs for world-state persistence events.

Payloads preserve event-specific snapshots. Universal event metadata is supplied
separately on decoding; replay does not read or write the referenced snapshot file.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.world_state_failure_reasons import WorldStateFailureReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.world_state_events import (
    WorldStateExported,
    WorldStateExportFailed,
    WorldStateImported,
)
from src.application.value_objects.world_state_entity_counts import WorldStateEntityCounts
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_non_negative_int,
    require_optional_positive_int,
    require_positive_int,
    require_str,
)


class WorldStateExportedEventPayloadCodec(EventPayloadCodec[WorldStateExported]):
    """Encode and decode the version-1 successful world-state export snapshot.

    Exactly six keys are required: snapshot_path, schema_version, and the four
    flat customer_count, package_count, route_count, and truck_count fields.
    Decoding reconstructs WorldStateEntityCounts from these non-negative integer
    counts. The positive snapshot schema_version is independent of this codec's
    event_version. Path text is preserved verbatim, without filesystem access.
    Encoding trusts typed event fields; decoding validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateExported]:
        """Return the concrete world-state-exported application event class."""
        return WorldStateExported

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_exported``."""
        return "world_state_exported"

    @property
    def event_version(self) -> int:
        """Return the payload contract version, not the snapshot schema version."""
        return 1

    def encode(self, event: WorldStateExported) -> JSONObject:
        """Serialize the export snapshot into a fresh, flat JSON object.

        Args:
            event: Version-1 event with correctly typed export fields.

        Returns:
            Unchanged snapshot path, integer schema version, and four integer
            counts. No nested entity_counts object or event/envelope metadata
            is included.
        """
        return {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "customer_count": event.entity_counts.customers,
            "package_count": event.entity_counts.packages,
            "route_count": event.entity_counts.routes,
            "truck_count": event.entity_counts.trucks,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateExported:
        """Validate an export payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the six version-1 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event containing a WorldStateEntityCounts value object and
            the original path and snapshot schema version. The input payload
            is neither mutated nor retained, and the path is not resolved.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans, strings, and floats are not valid counts or
                schema versions; snapshot_path must be a string.
            ValueError: If keys are missing or unexpected, schema_version is
                non-positive, any count is negative, or timestamps use the
                wrong time domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "snapshot_path",
            "schema_version",
            "customer_count",
            "package_count",
            "route_count",
            "truck_count",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_positive_int(payload["schema_version"], "schema_version")
        customer_count = require_non_negative_int(payload["customer_count"], "customer_count")
        package_count = require_non_negative_int(payload["package_count"], "package_count")
        route_count = require_non_negative_int(payload["route_count"], "route_count")
        truck_count = require_non_negative_int(payload["truck_count"], "truck_count")

        return WorldStateExported(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            entity_counts=WorldStateEntityCounts(
                customers=customer_count,
                packages=package_count,
                routes=route_count,
                trucks=truck_count,
            ),
        )


class WorldStateExportFailedEventPayloadCodec(EventPayloadCodec[WorldStateExportFailed]):
    """Encode and decode the version-1 failed world-state export snapshot.

    Payloads contain exactly snapshot_path, schema_version, and reason. An
    unknown snapshot schema version is represented by JSON null, not an omitted
    key. Known schema versions are positive integers, independent of the codec
    version. Reasons use WorldStateFailureReason values. Path text is preserved
    verbatim; replay neither accesses the filesystem nor retries the export.
    Encoding trusts typed event fields; decoding validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateExportFailed]:
        """Return the concrete failed-export application event class."""
        return WorldStateExportFailed

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_export_failed``."""
        return "world_state_export_failed"

    @property
    def event_version(self) -> int:
        """Return the payload contract version, not the snapshot schema version."""
        return 1

    def encode(self, event: WorldStateExportFailed) -> JSONObject:
        """Serialize the failed export into a fresh JSON object.

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
    ) -> WorldStateExportFailed:
        """Validate a failure payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the three version-1 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new failure event with a typed WorldStateFailureReason and the
            supplied metadata. The payload is neither mutated nor retained.

        Raises:
            TypeError: If the path or reason is not a string, schema_version
                is neither None nor an integer (excluding bool), or metadata
                has an invalid runtime type.
            ValueError: If keys are missing or unexpected, a supplied schema
                version is non-positive, the reason is unknown, or timestamps
                use the wrong time domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "snapshot_path",
            "schema_version",
            "reason",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_optional_positive_int(payload["schema_version"], "schema_version")
        reason = WorldStateFailureReason(require_str(payload["reason"], "reason"))

        return WorldStateExportFailed(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            reason=reason,
        )


class WorldStateImportedEventPayloadCodec(EventPayloadCodec[WorldStateImported]):
    """Encode and decode the version-2 successful world-state import snapshot.

    Exactly ten keys are required: snapshot_path, schema_version, and four
    previous_*_count and four new_*_count fields for customers, packages, routes,
    and trucks. Both count groups are non-negative integer snapshots, not deltas;
    counts may increase, decrease, or stay unchanged during an import.

    The positive snapshot schema_version is independent of event_version.
    Paths are preserved verbatim, and decoding does not read the snapshot file
    or perform an import. Encoding trusts typed event fields; decoding validates
    serialized values. This codec does not upgrade version-1 payloads.
    """

    @property
    def event_class(self) -> type[WorldStateImported]:
        """Return the concrete world-state-imported application event class."""
        return WorldStateImported

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_imported``."""
        return "world_state_imported"

    @property
    def event_version(self) -> int:
        """Return version 2, whose payload includes before and after counts."""
        return 2

    def encode(self, event: WorldStateImported) -> JSONObject:
        """Serialize both import count snapshots into a fresh, flat JSON object.

        Args:
            event: Version-2 event with correctly typed import fields.

        Returns:
            The unchanged path, integer snapshot schema version, and eight
            integer counts. No nested count objects or universal event metadata
            are included.
        """
        return {
            "snapshot_path": event.snapshot_path,
            "schema_version": event.schema_version,
            "previous_customer_count": event.previous_entity_counts.customers,
            "previous_package_count": event.previous_entity_counts.packages,
            "previous_route_count": event.previous_entity_counts.routes,
            "previous_truck_count": event.previous_entity_counts.trucks,
            "new_customer_count": event.new_entity_counts.customers,
            "new_package_count": event.new_entity_counts.packages,
            "new_route_count": event.new_entity_counts.routes,
            "new_truck_count": event.new_entity_counts.trucks,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateImported:
        """Validate an import payload and restore its original event metadata.

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
        expected_payload_keys: Final[frozenset[str]] = frozenset([
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

        require_json_object_keys(payload, expected_payload_keys)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_positive_int(payload["schema_version"], "schema_version")
        previous_customer_count = require_non_negative_int(
            payload["previous_customer_count"], "previous_customer_count"
        )
        previous_package_count = require_non_negative_int(
            payload["previous_package_count"], "previous_package_count"
        )
        previous_route_count = require_non_negative_int(payload["previous_route_count"], "previous_route_count")
        previous_truck_count = require_non_negative_int(payload["previous_truck_count"], "previous_truck_count")
        new_customer_count = require_non_negative_int(payload["new_customer_count"], "new_customer_count")
        new_package_count = require_non_negative_int(payload["new_package_count"], "new_package_count")
        new_route_count = require_non_negative_int(payload["new_route_count"], "new_route_count")
        new_truck_count = require_non_negative_int(payload["new_truck_count"], "new_truck_count")

        return WorldStateImported(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            previous_entity_counts=WorldStateEntityCounts(
                customers=previous_customer_count,
                packages=previous_package_count,
                routes=previous_route_count,
                trucks=previous_truck_count,
            ),
            new_entity_counts=WorldStateEntityCounts(
                customers=new_customer_count,
                packages=new_package_count,
                routes=new_route_count,
                trucks=new_truck_count,
            ),
        )
