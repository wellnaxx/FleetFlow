"""World-state runtime replacement and advancement outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.eventing.outbox.codecs.entity_counts import decode_entity_counts, encode_entity_counts
from src.application.events.world_state_events import WorldStateAdvanced, WorldStateRuntimeSwapped
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_non_negative_int, require_positive_int, require_str

_WORLD_STATE_RUNTIME_SWAPPED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
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


class WorldStateRuntimeSwappedEventPayloadCodec(EventPayloadCodec[WorldStateRuntimeSwapped]):
    """Encode and decode the version-2 runtime-replacement event.

    Payloads contain exactly snapshot_path, schema_version, and four
    previous_*_count and four new_*_count fields for customers, packages, routes,
    and trucks. These are non-negative count snapshots, not deltas; counts may
    increase, decrease, or remain unchanged when the runtime is replaced.

    The positive snapshot schema_version is independent of event_version.
    Paths are preserved verbatim. Decoding neither reads the snapshot nor
    replaces runtime state, and does not upgrade version-1 payloads. Encoding
    trusts typed event fields; decoding validates serialized values.
    """

    @property
    def event_class(self) -> type[WorldStateRuntimeSwapped]:
        """Return the concrete runtime-swapped application event class."""
        return WorldStateRuntimeSwapped

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_runtime_swapped``."""
        return "world_state_runtime_swapped"

    @property
    def event_version(self) -> int:
        """Return version 2, whose payload includes before and after counts."""
        return 2

    def encode(self, event: WorldStateRuntimeSwapped) -> JSONObject:
        """Serialize both runtime count snapshots into a fresh, flat JSON object.

        Args:
            event: Version-2 event with correctly typed runtime-swap fields.

        Returns:
            The unchanged snapshot path, integer schema version, and eight
            integer counts. No nested count objects or universal event metadata
            are included.
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
    ) -> WorldStateRuntimeSwapped:
        """Validate a runtime-swap payload and restore its original metadata.

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
        require_json_object_keys(payload, _WORLD_STATE_RUNTIME_SWAPPED_PAYLOAD_KEYS)

        snapshot_path = require_str(payload["snapshot_path"], "snapshot_path")
        schema_version = require_positive_int(payload["schema_version"], "schema_version")
        previous_entity_counts = decode_entity_counts(payload, prefix="previous_")
        new_entity_counts = decode_entity_counts(payload, prefix="new_")

        return WorldStateRuntimeSwapped(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            snapshot_path=snapshot_path,
            schema_version=schema_version,
            previous_entity_counts=previous_entity_counts,
            new_entity_counts=new_entity_counts,
        )


_WORLD_STATE_ADVANCED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "routes_updated",
    "packages_updated",
    "trucks_moved",
    "trucks_released",
    "trucks_reconciled",
])


class WorldStateAdvancedEventPayloadCodec(EventPayloadCodec[WorldStateAdvanced]):
    """Encode and decode the version-2 heartbeat advancement summary.

    Payloads contain exactly routes_updated, packages_updated, trucks_moved,
    trucks_released, and trucks_reconciled. Each is a non-negative integer
    counter, including zero when no corresponding change occurred. Encoding
    trusts typed event fields; decoding validates each counter independently.
    Replay reconstructs the summary without advancing the world. Version-1
    payloads are not upgraded here.
    """

    @property
    def event_class(self) -> type[WorldStateAdvanced]:
        """Return the concrete world-state-advanced application event class."""
        return WorldStateAdvanced

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``world_state_advanced``."""
        return "world_state_advanced"

    @property
    def event_version(self) -> int:
        """Return version 2 of the five-counter advancement payload contract."""
        return 2

    def encode(self, event: WorldStateAdvanced) -> JSONObject:
        """Serialize the heartbeat counters into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed advancement counters.

        Returns:
            Five integer counters, without universal event metadata or snapshot
            persistence fields.
        """
        return {
            "routes_updated": event.routes_updated,
            "packages_updated": event.packages_updated,
            "trucks_moved": event.trucks_moved,
            "trucks_released": event.trucks_released,
            "trucks_reconciled": event.trucks_reconciled,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> WorldStateAdvanced:
        """Validate an advancement payload and restore its original metadata.

        Args:
            payload: JSON object containing exactly the five version-2 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new summary event with the supplied counters and metadata. The
            input payload is neither mutated nor retained.

        Raises:
            TypeError: If a counter is not an integer (excluding bool), or
                metadata has an invalid runtime type. Values are not coerced.
            ValueError: If keys are missing or unexpected, any counter is
                negative, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _WORLD_STATE_ADVANCED_PAYLOAD_KEYS)

        routes_updated = require_non_negative_int(payload["routes_updated"], "routes_updated")
        packages_updated = require_non_negative_int(payload["packages_updated"], "packages_updated")
        trucks_moved = require_non_negative_int(payload["trucks_moved"], "trucks_moved")
        trucks_released = require_non_negative_int(payload["trucks_released"], "trucks_released")
        trucks_reconciled = require_non_negative_int(payload["trucks_reconciled"], "trucks_reconciled")

        return WorldStateAdvanced(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            routes_updated=routes_updated,
            packages_updated=packages_updated,
            trucks_moved=trucks_moved,
            trucks_released=trucks_released,
            trucks_reconciled=trucks_reconciled,
        )
