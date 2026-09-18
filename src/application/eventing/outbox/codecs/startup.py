"""Outbox payload codecs for startup workflow events.

Only event-specific data is serialized. Universal event metadata is supplied
separately on decoding; actor and envelope metadata stays outside the payload.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.startup_events import FleetSeeded
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_list,
    require_positive_int,
    require_str,
)


class FleetSeededEventPayloadCodec(EventPayloadCodec[FleetSeeded]):
    """Encode and decode the version-2 fleet-seeding snapshot.

    Exactly seeded_truck_ids and backend are required. IDs form an ordered JSON
    array of positive integers without seeded-fleet range restrictions. Backend
    text is preserved verbatim, not parsed against current configuration options.
    Encoding trusts typed event fields; decoding restores the snapshot without
    reseeding trucks, sorting or deduplicating IDs, or imposing a minimum count.
    truck_count is derived by the event and is not a persisted payload field.
    """

    @property
    def event_class(self) -> type[FleetSeeded]:
        """Return the concrete fleet-seeded application event class."""
        return FleetSeeded

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``fleet_seeded``."""
        return "fleet_seeded"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: FleetSeeded) -> JSONObject:
        """Serialize the seeded fleet snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed seeding fields.

        Returns:
            A fresh list of integer truck IDs and the unchanged backend string.
            Derived truck_count and event and envelope metadata are excluded.
        """
        return {
            "seeded_truck_ids": list(event.seeded_truck_ids),
            "backend": event.backend,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> FleetSeeded:
        """Validate a seeding payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly seeded_truck_ids and backend.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event containing an ordered tuple of truck IDs and unchanged
            backend text. The payload and its ID list are neither mutated nor
            retained; truck_count follows the restored tuple length.

        Raises:
            TypeError: If IDs are not supplied as a list, an ID is not an integer
                or is a boolean, backend is not a string, or metadata has an
                invalid runtime type. ID errors identify the list index.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                or timestamps use the wrong time domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset(["seeded_truck_ids", "backend"])

        require_json_object_keys(payload, expected_payload_keys)

        raw_seeded_truck_ids = require_list(payload["seeded_truck_ids"], "seeded_truck_ids")
        seeded_truck_ids: list[int] = []
        for index, truck_id in enumerate(raw_seeded_truck_ids):
            field_name = f"seeded_truck_ids[{index}]"
            validated_truck_id = require_positive_int(truck_id, field_name)
            seeded_truck_ids.append(validated_truck_id)

        backend = require_str(payload["backend"], "backend")

        return FleetSeeded(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            seeded_truck_ids=tuple(seeded_truck_ids),
            backend=backend,
        )
