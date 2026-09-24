"""Route truck assignment and release outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.truck_release_reasons import TruckReleaseReason
from src.domain.enums.truck_status import TruckStatus
from src.domain.events.route_events import TruckAssignedToRoute, TruckReleasedFromRoute
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_deserialization import parse_enum_value, parse_optional_naive_datetime
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_optional_positive_int, require_positive_int, require_str

_TRUCK_ASSIGNED_TO_ROUTE_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "truck_id",
    "previous_route_id",
    "new_route_id",
    "previous_status",
    "new_status",
    "previous_location",
    "new_location",
    "previous_busy_from",
    "new_busy_from",
    "previous_busy_until",
    "new_busy_until",
])


class TruckAssignedToRouteEventPayloadCodec(EventPayloadCodec[TruckAssignedToRoute]):
    """Encode and decode the version-2 truck assignment snapshot.

    All eleven payload keys are required. previous_route_id and the four busy
    timestamps may independently be null; truck_id and new_route_id must be
    positive integers. IDs are not restricted to the seeded fleet's range.
    Encoding trusts typed event fields. Decoding restores serialized values
    without consulting live entities or reapplying truck-assignment policies.
    """

    @property
    def event_class(self) -> type[TruckAssignedToRoute]:
        """Return the concrete truck-assigned-to-route event class."""
        return TruckAssignedToRoute

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``truck_assigned_to_route``."""
        return "truck_assigned_to_route"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: TruckAssignedToRoute) -> JSONObject:
        """Serialize assignment before/after values into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed assignment fields.

        Returns:
            Integer IDs, string statuses and locations, and ISO-formatted busy
            timestamps with microseconds preserved. Absent previous route and
            busy timestamps become JSON null. Event and envelope metadata are
            excluded.
        """
        return {
            "truck_id": event.truck_id,
            "previous_route_id": event.previous_route_id,
            "new_route_id": event.new_route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_busy_from": optional_isoformat(event.previous_busy_from),
            "new_busy_from": optional_isoformat(event.new_busy_from),
            "previous_busy_until": optional_isoformat(event.previous_busy_until),
            "new_busy_until": optional_isoformat(event.new_busy_until),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> TruckAssignedToRoute:
        """Validate an assignment payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the eleven version-2 keys.
                Nullable fields must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving before/after route IDs, typed statuses and
            locations, and optional naive busy timestamps. The input payload
            is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, truck_id and new_route_id
                cannot be null, and non-null busy timestamps must be strings.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                a status is unknown, timestamp text is invalid, or timestamps
                use the wrong time domain.
            DomainValidationError: If either location is blank after normalization.
        """
        require_json_object_keys(payload, _TRUCK_ASSIGNED_TO_ROUTE_PAYLOAD_KEYS)

        truck_id = require_positive_int(payload["truck_id"], "truck_id")
        previous_route_id = require_optional_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_positive_int(payload["new_route_id"], "new_route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", TruckStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", TruckStatus)
        previous_location = LocationCode(require_str(payload["previous_location"], "previous_location"))
        new_location = LocationCode(require_str(payload["new_location"], "new_location"))
        previous_busy_from = parse_optional_naive_datetime(payload["previous_busy_from"], "previous_busy_from")
        new_busy_from = parse_optional_naive_datetime(payload["new_busy_from"], "new_busy_from")
        previous_busy_until = parse_optional_naive_datetime(
            payload["previous_busy_until"], "previous_busy_until"
        )
        new_busy_until = parse_optional_naive_datetime(payload["new_busy_until"], "new_busy_until")

        return TruckAssignedToRoute(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            truck_id=truck_id,
            previous_route_id=previous_route_id,
            new_route_id=new_route_id,
            previous_status=previous_status,
            new_status=new_status,
            previous_location=previous_location,
            new_location=new_location,
            previous_busy_from=previous_busy_from,
            new_busy_from=new_busy_from,
            previous_busy_until=previous_busy_until,
            new_busy_until=new_busy_until,
        )


_TRUCK_RELEASED_FROM_ROUTE_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "truck_id",
    "previous_route_id",
    "new_route_id",
    "previous_status",
    "new_status",
    "previous_location",
    "new_location",
    "previous_busy_from",
    "new_busy_from",
    "previous_busy_until",
    "new_busy_until",
    "reason",
])


class TruckReleasedFromRouteEventPayloadCodec(EventPayloadCodec[TruckReleasedFromRoute]):
    """Encode and decode the version-2 truck release snapshot.

    All twelve payload keys are required. new_route_id and the four busy
    timestamps may independently be null; truck_id and previous_route_id are
    positive integers without seeded-fleet range restrictions. Statuses and
    release reason use their enum values. Encoding trusts typed event fields;
    decoding validates serialized values without consulting live entities or
    reapplying truck-release policies.
    """

    @property
    def event_class(self) -> type[TruckReleasedFromRoute]:
        """Return the concrete truck-released-from-route event class."""
        return TruckReleasedFromRoute

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``truck_released_from_route``."""
        return "truck_released_from_route"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: TruckReleasedFromRoute) -> JSONObject:
        """Serialize release before/after values into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed release fields.

        Returns:
            Integer IDs, string statuses, locations and reason, and ISO-formatted
            busy timestamps with microseconds preserved. Absent new route and
            busy timestamps become JSON null. Event and envelope metadata are
            excluded.
        """
        return {
            "truck_id": event.truck_id,
            "previous_route_id": event.previous_route_id,
            "new_route_id": event.new_route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_busy_from": optional_isoformat(event.previous_busy_from),
            "new_busy_from": optional_isoformat(event.new_busy_from),
            "previous_busy_until": optional_isoformat(event.previous_busy_until),
            "new_busy_until": optional_isoformat(event.new_busy_until),
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> TruckReleasedFromRoute:
        """Validate a release payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the twelve version-2 keys.
                Nullable fields must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving before/after route IDs, typed statuses and
            locations, optional naive busy timestamps, and the typed release
            reason. The input payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, truck_id and previous_route_id
                cannot be null, and non-null busy timestamps must be strings.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                a status or reason is unknown, timestamp text is invalid, or
                timestamps use the wrong time domain.
            DomainValidationError: If either location is blank after normalization.
        """
        require_json_object_keys(payload, _TRUCK_RELEASED_FROM_ROUTE_PAYLOAD_KEYS)

        truck_id = require_positive_int(payload["truck_id"], "truck_id")
        previous_route_id = require_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_optional_positive_int(payload["new_route_id"], "new_route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", TruckStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", TruckStatus)
        previous_location = LocationCode(require_str(payload["previous_location"], "previous_location"))
        new_location = LocationCode(require_str(payload["new_location"], "new_location"))
        previous_busy_from = parse_optional_naive_datetime(payload["previous_busy_from"], "previous_busy_from")
        new_busy_from = parse_optional_naive_datetime(payload["new_busy_from"], "new_busy_from")
        previous_busy_until = parse_optional_naive_datetime(
            payload["previous_busy_until"], "previous_busy_until"
        )
        new_busy_until = parse_optional_naive_datetime(payload["new_busy_until"], "new_busy_until")
        reason = parse_enum_value(payload["reason"], "reason", TruckReleaseReason)

        return TruckReleasedFromRoute(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            truck_id=truck_id,
            previous_route_id=previous_route_id,
            new_route_id=new_route_id,
            previous_status=previous_status,
            new_status=new_status,
            previous_location=previous_location,
            new_location=new_location,
            previous_busy_from=previous_busy_from,
            new_busy_from=new_busy_from,
            previous_busy_until=previous_busy_until,
            new_busy_until=new_busy_until,
            reason=reason,
        )
