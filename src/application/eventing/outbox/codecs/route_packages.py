"""Route package assignment and detachment outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.events.route_events import PackageAssignedToRoute, PackageDetachedFromRoute
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_deserialization import parse_enum_value, parse_optional_naive_datetime
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_optional_positive_int, require_positive_int, require_str

_PACKAGE_ASSIGNED_TO_ROUTE_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "package_id",
    "previous_route_id",
    "new_route_id",
    "previous_expected_arrival",
    "new_expected_arrival",
])


class PackageAssignedToRouteEventPayloadCodec(EventPayloadCodec[PackageAssignedToRoute]):
    """Encode and decode the version-2 package-to-route assignment snapshot.

    All five payload keys are required. previous_route_id and both expected
    arrival times may independently be null; package_id and new_route_id must
    be positive integers. Encoding trusts typed event fields. Decoding validates
    serialized values without looking up live entities, recalculating arrival
    times, or reapplying package-assignment policies.
    """

    @property
    def event_class(self) -> type[PackageAssignedToRoute]:
        """Return the concrete package-assigned-to-route event class."""
        return PackageAssignedToRoute

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``package_assigned_to_route``."""
        return "package_assigned_to_route"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: PackageAssignedToRoute) -> JSONObject:
        """Serialize the assignment's before/after values into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed assignment fields.

        Returns:
            Integer package and route IDs, and ISO-formatted expected arrivals
            with microseconds preserved. Absent previous route and arrival
            values become JSON null. Event and envelope metadata are excluded.
        """
        return {
            "package_id": event.package_id,
            "previous_route_id": event.previous_route_id,
            "new_route_id": event.new_route_id,
            "previous_expected_arrival": optional_isoformat(event.previous_expected_arrival),
            "new_expected_arrival": optional_isoformat(event.new_expected_arrival),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> PackageAssignedToRoute:
        """Validate an assignment payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the five version-2 keys.
                Nullable fields must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving the previous and new route IDs and optional
            naive arrival times. The input payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, package_id and new_route_id
                cannot be null, and non-null arrivals must be strings.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                arrival text is invalid, or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _PACKAGE_ASSIGNED_TO_ROUTE_PAYLOAD_KEYS)

        package_id = require_positive_int(payload["package_id"], "package_id")
        previous_route_id = require_optional_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_positive_int(payload["new_route_id"], "new_route_id")
        previous_expected_arrival = parse_optional_naive_datetime(
            payload["previous_expected_arrival"], "previous_expected_arrival"
        )
        new_expected_arrival = parse_optional_naive_datetime(
            payload["new_expected_arrival"], "new_expected_arrival"
        )

        return PackageAssignedToRoute(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            package_id=package_id,
            previous_route_id=previous_route_id,
            new_route_id=new_route_id,
            previous_expected_arrival=previous_expected_arrival,
            new_expected_arrival=new_expected_arrival,
        )


_PACKAGE_DETACHED_FROM_ROUTE_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "package_id",
    "previous_route_id",
    "new_route_id",
    "previous_status",
    "new_status",
    "previous_location",
    "new_location",
    "previous_expected_arrival",
    "new_expected_arrival",
    "reason",
])


class PackageDetachedFromRouteEventPayloadCodec(EventPayloadCodec[PackageDetachedFromRoute]):
    """Encode and decode the version-2 package detachment snapshot.

    All ten payload keys are required. new_route_id and both expected arrivals
    may independently be null; package_id and previous_route_id are positive
    integers. Statuses and detachment reason use their enum values. Encoding
    trusts typed event fields; decoding validates serialized values without
    consulting live entities or reapplying detachment policies.
    """

    @property
    def event_class(self) -> type[PackageDetachedFromRoute]:
        """Return the concrete package-detached-from-route event class."""
        return PackageDetachedFromRoute

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``package_detached_from_route``."""
        return "package_detached_from_route"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: PackageDetachedFromRoute) -> JSONObject:
        """Serialize the detachment's before/after values into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed detachment fields.

        Returns:
            Integer IDs, string statuses, locations and reason, and ISO-formatted
            arrivals with microseconds preserved. Absent new route and arrival
            values become JSON null. Event and envelope metadata are excluded.
        """
        return {
            "package_id": event.package_id,
            "previous_route_id": event.previous_route_id,
            "new_route_id": event.new_route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_expected_arrival": optional_isoformat(event.previous_expected_arrival),
            "new_expected_arrival": optional_isoformat(event.new_expected_arrival),
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> PackageDetachedFromRoute:
        """Validate a detachment payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the ten version-2 keys.
                Nullable fields must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving before/after IDs, typed statuses and locations,
            optional naive arrivals, and the typed detachment reason. The input
            payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, package_id and previous_route_id
                cannot be null, and non-null arrivals must be strings.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                a status or reason is unknown, arrival text is invalid, or
                timestamps use the wrong time domain.
            DomainValidationError: If either location is blank after normalization.
        """
        require_json_object_keys(payload, _PACKAGE_DETACHED_FROM_ROUTE_PAYLOAD_KEYS)

        package_id = require_positive_int(payload["package_id"], "package_id")
        previous_route_id = require_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_optional_positive_int(payload["new_route_id"], "new_route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", ItemStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", ItemStatus)
        previous_location = LocationCode(require_str(payload["previous_location"], "previous_location"))
        new_location = LocationCode(require_str(payload["new_location"], "new_location"))
        previous_expected_arrival = parse_optional_naive_datetime(
            payload["previous_expected_arrival"], "previous_expected_arrival"
        )
        new_expected_arrival = parse_optional_naive_datetime(
            payload["new_expected_arrival"], "new_expected_arrival"
        )
        reason = parse_enum_value(payload["reason"], "reason", PackageDetachmentReason)

        return PackageDetachedFromRoute(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            package_id=package_id,
            previous_route_id=previous_route_id,
            new_route_id=new_route_id,
            previous_status=previous_status,
            new_status=new_status,
            previous_location=previous_location,
            new_location=new_location,
            previous_expected_arrival=previous_expected_arrival,
            new_expected_arrival=new_expected_arrival,
            reason=reason,
        )
