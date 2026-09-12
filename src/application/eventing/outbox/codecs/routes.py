"""Outbox payload codecs for delivery-route lifecycle events.

Only event-specific snapshots are serialized. Universal event metadata is
supplied separately on decoding; business timestamps remain naive app-local.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import RouteCreated
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_list,
    require_naive_datetime,
    require_positive_int,
    require_str,
)


class RouteCreatedEventPayloadCodec(EventPayloadCodec[RouteCreated]):
    """Encode and decode the version-2 route-creation snapshot.

    All five payload keys are required, including the two nullable timestamps.
    The route ID is a positive integer, locations are an ordered JSON array of
    strings, and initial_status uses a RouteStatus value. Encoding trusts typed
    event fields. Decoding restores typed locations without consulting the map,
    building a schedule, or reapplying route-path and lifecycle policies.
    """

    @property
    def event_class(self) -> type[RouteCreated]:
        """Return the concrete route-created event class."""
        return RouteCreated

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_created``."""
        return "route_created"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: RouteCreated) -> JSONObject:
        """Serialize a route-creation snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed snapshot fields.

        Returns:
            Integer route ID, a fresh ordered list of location strings, string
            status, and ISO-formatted departure and completion timestamps or
            JSON null. Microseconds are preserved; event and envelope metadata
            are excluded.
        """
        return {
            "route_id": event.route_id,
            "locations": [str(location) for location in event.locations],
            "departure_time": optional_isoformat(event.departure_time),
            "initial_status": event.initial_status.value,
            "expected_completion_time": optional_isoformat(event.expected_completion_time),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteCreated:
        """Validate a route payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the five version-2 keys.
                Both timestamp keys must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with an ordered tuple of normalized LocationCode values,
            a typed status, and optional naive timestamps. The input object and
            its location list are neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Locations must be a list of strings, IDs cannot be
                booleans, and non-null timestamps must be strings.
            ValueError: If keys are missing or unexpected, route_id is
                non-positive, status is unknown, timestamp text is invalid,
                or timestamps use the wrong time domain.
            DomainValidationError: If any location is blank after normalization.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "route_id",
            "locations",
            "departure_time",
            "initial_status",
            "expected_completion_time",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        route_id = require_positive_int(payload["route_id"], "route_id")

        raw_locations = require_list(payload["locations"], "locations")
        locations: list[LocationCode] = []
        for index, item in enumerate(raw_locations):
            field_name = f"locations[{index}]"
            name = require_str(item, field_name)
            locations.append(LocationCode(name))

        departure_time = None
        if payload["departure_time"] is not None:
            departure_text = require_str(payload["departure_time"], "departure_time")
            try:
                parsed_departure = datetime.fromisoformat(departure_text)
            except ValueError as exc:
                raise ValueError("departure_time: expected ISO-formatted datetime.") from exc
            departure_time = require_naive_datetime(parsed_departure, "departure_time")

        initial_status = RouteStatus(require_str(payload["initial_status"], "initial_status"))

        expected_completion_time = None
        if payload["expected_completion_time"] is not None:
            completion_text = require_str(payload["expected_completion_time"], "expected_completion_time")
            try:
                parsed_completion = datetime.fromisoformat(completion_text)
            except ValueError as exc:
                raise ValueError("expected_completion_time: expected ISO-formatted datetime.") from exc
            expected_completion_time = require_naive_datetime(parsed_completion, "expected_completion_time")

        return RouteCreated(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            locations=tuple(locations),
            departure_time=departure_time,
            initial_status=initial_status,
            expected_completion_time=expected_completion_time,
        )
