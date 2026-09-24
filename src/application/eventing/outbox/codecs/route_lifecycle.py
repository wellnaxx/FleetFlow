"""Route creation, scheduling, execution, and removal outbox payload codecs.

Payloads contain event-specific fields only. Universal metadata is supplied
separately when decoding; wire versions and field validation remain codec-specific.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import (
    RouteCompleted,
    RouteCreated,
    RouteRemoved,
    RouteScheduled,
    RouteStarted,
)
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_deserialization import (
    parse_enum_value,
    parse_naive_datetime,
    parse_optional_naive_datetime,
)
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_list, require_optional_positive_int, require_positive_int, require_str

_ROUTE_CREATED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "route_id",
    "locations",
    "departure_time",
    "initial_status",
    "expected_completion_time",
])


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
        require_json_object_keys(payload, _ROUTE_CREATED_PAYLOAD_KEYS)

        route_id = require_positive_int(payload["route_id"], "route_id")

        raw_locations = require_list(payload["locations"], "locations")
        locations: list[LocationCode] = []
        for index, item in enumerate(raw_locations):
            field_name = f"locations[{index}]"
            name = require_str(item, field_name)
            locations.append(LocationCode(name))

        departure_time = parse_optional_naive_datetime(payload["departure_time"], "departure_time")

        initial_status = parse_enum_value(payload["initial_status"], "initial_status", RouteStatus)

        expected_completion_time = parse_optional_naive_datetime(
            payload["expected_completion_time"], "expected_completion_time"
        )

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


_ROUTE_SCHEDULED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "route_id",
    "previous_status",
    "new_status",
    "previous_departure_time",
    "new_departure_time",
    "previous_expected_completion_time",
    "new_expected_completion_time",
])


class RouteScheduledEventPayloadCodec(EventPayloadCodec[RouteScheduled]):
    """Encode and decode the version-2 route scheduling transition snapshot.

    All seven payload keys are required. Previous departure and completion
    times may independently be null; both new timestamps must be present and
    non-null. IDs are positive integers and statuses use RouteStatus values.
    Encoding trusts typed event fields. Decoding validates serialized values
    without rebuilding schedules or reapplying lifecycle and timing policies.
    """

    @property
    def event_class(self) -> type[RouteScheduled]:
        """Return the concrete route-scheduled event class."""
        return RouteScheduled

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_scheduled``."""
        return "route_scheduled"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: RouteScheduled) -> JSONObject:
        """Serialize the scheduling before/after snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed transition fields.

        Returns:
            Integer route ID, string status values, and ISO-formatted timestamps
            with microseconds preserved. Absent previous times become JSON null.
            Event and envelope metadata are excluded.
        """
        return {
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_departure_time": optional_isoformat(event.previous_departure_time),
            "new_departure_time": event.new_departure_time.isoformat(),
            "previous_expected_completion_time": optional_isoformat(event.previous_expected_completion_time),
            "new_expected_completion_time": event.new_expected_completion_time.isoformat(),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteScheduled:
        """Validate a scheduling payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the seven version-2 keys.
                Only the two previous timestamps may be null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with typed before/after statuses and naive business
            timestamps. Scheduled times are preserved independently of occurrence
            time. The input payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, new timestamps cannot be null,
                and non-null timestamps must be strings rather than datetimes.
            ValueError: If keys are missing or unexpected, route_id is
                non-positive, a status is unknown, timestamp text is invalid,
                or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _ROUTE_SCHEDULED_PAYLOAD_KEYS)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", RouteStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", RouteStatus)

        previous_departure_time = parse_optional_naive_datetime(
            payload["previous_departure_time"], "previous_departure_time"
        )

        new_departure_time = parse_naive_datetime(payload["new_departure_time"], "new_departure_time")

        previous_expected_completion_time = parse_optional_naive_datetime(
            payload["previous_expected_completion_time"], "previous_expected_completion_time"
        )

        new_expected_completion_time = parse_naive_datetime(
            payload["new_expected_completion_time"], "new_expected_completion_time"
        )

        return RouteScheduled(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            previous_status=previous_status,
            new_status=new_status,
            previous_departure_time=previous_departure_time,
            new_departure_time=new_departure_time,
            previous_expected_completion_time=previous_expected_completion_time,
            new_expected_completion_time=new_expected_completion_time,
        )


_ROUTE_STARTED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "route_id",
    "previous_status",
    "new_status",
])


class RouteStartedEventPayloadCodec(EventPayloadCodec[RouteStarted]):
    """Encode and decode the version-2 route-start transition snapshot.

    Exactly route_id, previous_status, and new_status are required. The route
    ID is a positive integer and statuses use RouteStatus values. Encoding
    trusts typed event fields; decoding validates serialized representations
    without consulting live routes or reapplying transition eligibility rules.
    Occurrence time remains separate event metadata, not a payload field.
    """

    @property
    def event_class(self) -> type[RouteStarted]:
        """Return the concrete route-started event class."""
        return RouteStarted

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_started``."""
        return "route_started"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: RouteStarted) -> JSONObject:
        """Serialize the route's before/after statuses into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed transition fields.

        Returns:
            Integer route ID and string previous/new status values. Event and
            envelope metadata, including occurrence time, are excluded.
        """
        return {
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteStarted:
        """Validate a route-start payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the three version-2 keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving the route ID and typed before/after statuses.
            The input payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. A null, boolean, float, or string is not a valid route ID.
            ValueError: If keys are missing or unexpected, route_id is
                non-positive, a status is unknown, or timestamps use the wrong
                time domain.
        """
        require_json_object_keys(payload, _ROUTE_STARTED_PAYLOAD_KEYS)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", RouteStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", RouteStatus)

        return RouteStarted(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            previous_status=previous_status,
            new_status=new_status,
        )


_ROUTE_COMPLETED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "route_id",
    "previous_status",
    "new_status",
    "departure_time",
    "expected_completion_time",
])


class RouteCompletedEventPayloadCodec(EventPayloadCodec[RouteCompleted]):
    """Encode and decode the version-2 route completion snapshot.

    All five payload keys are required and non-null. The route ID is a positive
    integer, statuses use RouteStatus values, and both schedule timestamps are
    naive app-local datetimes. Expected completion remains separate from event
    occurrence time. Encoding trusts typed fields; decoding validates serialized
    values without rebuilding schedules or reapplying transition policies.
    """

    @property
    def event_class(self) -> type[RouteCompleted]:
        """Return the concrete route-completed event class."""
        return RouteCompleted

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_completed``."""
        return "route_completed"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: RouteCompleted) -> JSONObject:
        """Serialize the completion snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed completion fields.

        Returns:
            Integer route ID, string before/after status values, and
            ISO-formatted departure and expected completion times with
            microseconds preserved. Event and envelope metadata are excluded.
        """
        return {
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "departure_time": event.departure_time.isoformat(),
            "expected_completion_time": event.expected_completion_time.isoformat(),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteCompleted:
        """Validate a completion payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the five version-2 keys.
                Neither schedule timestamp may be null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving the route ID, typed before/after statuses,
            and naive schedule timestamps. The input payload is neither mutated
            nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not valid IDs, and schedule timestamps must
                be strings rather than null or datetime objects.
            ValueError: If keys are missing or unexpected, route_id is
                non-positive, a status is unknown, timestamp text is invalid,
                or timestamps use the wrong time domain.
        """
        require_json_object_keys(payload, _ROUTE_COMPLETED_PAYLOAD_KEYS)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", RouteStatus)
        new_status = parse_enum_value(payload["new_status"], "new_status", RouteStatus)
        departure_time = parse_naive_datetime(payload["departure_time"], "departure_time")
        expected_completion_time = parse_naive_datetime(
            payload["expected_completion_time"], "expected_completion_time"
        )

        return RouteCompleted(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            previous_status=previous_status,
            new_status=new_status,
            departure_time=departure_time,
            expected_completion_time=expected_completion_time,
        )


_ROUTE_REMOVED_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset([
    "route_id",
    "previous_status",
    "previous_locations",
    "previous_departure_time",
    "previous_expected_completion_time",
    "detached_package_ids",
    "released_truck_id",
])


class RouteRemovedEventPayloadCodec(EventPayloadCodec[RouteRemoved]):
    """Encode and decode the version-2 route removal snapshot.

    All seven payload keys are required. Previous schedule timestamps and the
    released truck ID may independently be null. Locations and detached package
    IDs are ordered JSON arrays, restored as tuples on decoding. IDs are positive
    integers without seeded-fleet restrictions. Encoding trusts typed fields;
    decoding validates representations without consulting live entities or
    reapplying route-path, scheduling, or removal policies.
    """

    @property
    def event_class(self) -> type[RouteRemoved]:
        """Return the concrete route-removed event class."""
        return RouteRemoved

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_removed``."""
        return "route_removed"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: RouteRemoved) -> JSONObject:
        """Serialize the pre-removal snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed removal fields.

        Returns:
            Integer IDs, string status, fresh lists of location strings and
            detached package IDs, and ISO-formatted schedule timestamps with
            microseconds preserved. Absent truck and timestamp values become
            JSON null. Event and envelope metadata are excluded.
        """
        return {
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "previous_locations": [str(location) for location in event.previous_locations],
            "previous_departure_time": optional_isoformat(event.previous_departure_time),
            "previous_expected_completion_time": optional_isoformat(event.previous_expected_completion_time),
            "detached_package_ids": list(event.detached_package_ids),
            "released_truck_id": event.released_truck_id,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteRemoved:
        """Validate a removal payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the seven version-2 keys.
                Nullable fields must be present even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with typed status, ordered location and package-ID tuples,
            optional naive schedule timestamps, and optional released truck ID.
            The payload and its lists are neither mutated nor retained.

        Raises:
            TypeError: If a field or metadata has an invalid runtime type.
                Locations and package IDs must be lists with correctly typed
                elements; booleans are not valid IDs and non-null timestamps
                must be strings.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                status is unknown, timestamp text is invalid, or timestamps use
                the wrong time domain.
            DomainValidationError: If any location is blank after normalization.
        """
        require_json_object_keys(payload, _ROUTE_REMOVED_PAYLOAD_KEYS)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = parse_enum_value(payload["previous_status"], "previous_status", RouteStatus)
        raw_previous_locations = require_list(payload["previous_locations"], "previous_locations")
        previous_locations: list[LocationCode] = []
        for index, item in enumerate(raw_previous_locations):
            field_name = f"previous_locations[{index}]"
            name = require_str(item, field_name)
            previous_locations.append(LocationCode(name))
        previous_departure_time = parse_optional_naive_datetime(
            payload["previous_departure_time"], "previous_departure_time"
        )
        previous_expected_completion_time = parse_optional_naive_datetime(
            payload["previous_expected_completion_time"], "previous_expected_completion_time"
        )
        raw_detached_package_ids = require_list(payload["detached_package_ids"], "detached_package_ids")
        detached_package_ids: list[int] = []
        for index, package_id in enumerate(raw_detached_package_ids):
            field_name = f"detached_package_ids[{index}]"
            package_id = require_positive_int(package_id, field_name)
            detached_package_ids.append(package_id)
        released_truck_id = require_optional_positive_int(payload["released_truck_id"], "released_truck_id")

        return RouteRemoved(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            previous_status=previous_status,
            previous_locations=tuple(previous_locations),
            previous_departure_time=previous_departure_time,
            previous_expected_completion_time=previous_expected_completion_time,
            detached_package_ids=tuple(detached_package_ids),
            released_truck_id=released_truck_id,
        )
