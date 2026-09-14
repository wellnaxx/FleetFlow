"""Outbox payload codecs for delivery-route lifecycle events.

Only event-specific snapshots are serialized. Universal event metadata is
supplied separately on decoding; business timestamps remain naive app-local.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.package_detachment_reasons import PackageDetachmentReason
from src.domain.enums.route_status import RouteStatus
from src.domain.events.route_events import (
    PackageAssignedToRoute,
    PackageDetachedFromRoute,
    RouteCreated,
    RouteScheduled,
)
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_list,
    require_naive_datetime,
    require_optional_positive_int,
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
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "route_id",
            "previous_status",
            "new_status",
            "previous_departure_time",
            "new_departure_time",
            "previous_expected_completion_time",
            "new_expected_completion_time",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = RouteStatus(require_str(payload["previous_status"], "previous_status"))
        new_status = RouteStatus(require_str(payload["new_status"], "new_status"))

        previous_departure_time = None
        if payload["previous_departure_time"] is not None:
            departure_text = require_str(payload["previous_departure_time"], "previous_departure_time")
            try:
                parsed_departure = datetime.fromisoformat(departure_text)
            except ValueError as exc:
                raise ValueError("previous_departure_time: expected ISO-formatted datetime.") from exc
            previous_departure_time = require_naive_datetime(parsed_departure, "previous_departure_time")

        new_departure_text = require_str(payload["new_departure_time"], "new_departure_time")
        try:
            parsed_departure = datetime.fromisoformat(new_departure_text)
        except ValueError as exc:
            raise ValueError("new_departure_time: expected ISO-formatted datetime.") from exc
        new_departure_time = require_naive_datetime(parsed_departure, "new_departure_time")

        previous_expected_completion_time = None
        if payload["previous_expected_completion_time"] is not None:
            completion_text = require_str(
                payload["previous_expected_completion_time"], "previous_expected_completion_time"
            )
            try:
                parsed_completion = datetime.fromisoformat(completion_text)
            except ValueError as exc:
                raise ValueError("previous_expected_completion_time: expected ISO-formatted datetime.") from exc
            previous_expected_completion_time = require_naive_datetime(
                parsed_completion, "previous_expected_completion_time"
            )

        new_completion_text = require_str(
            payload["new_expected_completion_time"], "new_expected_completion_time"
        )
        try:
            parsed_completion = datetime.fromisoformat(new_completion_text)
        except ValueError as exc:
            raise ValueError("new_expected_completion_time: expected ISO-formatted datetime.") from exc
        new_expected_completion_time = require_naive_datetime(parsed_completion, "new_expected_completion_time")

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
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "package_id",
            "previous_route_id",
            "new_route_id",
            "previous_expected_arrival",
            "new_expected_arrival",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        package_id = require_positive_int(payload["package_id"], "package_id")
        previous_route_id = require_optional_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_positive_int(payload["new_route_id"], "new_route_id")
        previous_expected_arrival = None
        if payload["previous_expected_arrival"] is not None:
            arrival_text = require_str(payload["previous_expected_arrival"], "previous_expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("previous_expected_arrival: expected ISO-formatted datetime.") from exc
            previous_expected_arrival = require_naive_datetime(parsed_arrival, "previous_expected_arrival")
        new_expected_arrival = None
        if payload["new_expected_arrival"] is not None:
            arrival_text = require_str(payload["new_expected_arrival"], "new_expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("new_expected_arrival: expected ISO-formatted datetime.") from exc
            new_expected_arrival = require_naive_datetime(parsed_arrival, "new_expected_arrival")

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
        expected_payload_keys: Final[frozenset[str]] = frozenset([
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

        require_json_object_keys(payload, expected_payload_keys)

        package_id = require_positive_int(payload["package_id"], "package_id")
        previous_route_id = require_positive_int(payload["previous_route_id"], "previous_route_id")
        new_route_id = require_optional_positive_int(payload["new_route_id"], "new_route_id")
        previous_status = ItemStatus(require_str(payload["previous_status"], "previous_status"))
        new_status = ItemStatus(require_str(payload["new_status"], "new_status"))
        previous_location = LocationCode(require_str(payload["previous_location"], "previous_location"))
        new_location = LocationCode(require_str(payload["new_location"], "new_location"))
        previous_expected_arrival = None
        if payload["previous_expected_arrival"] is not None:
            arrival_text = require_str(payload["previous_expected_arrival"], "previous_expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("previous_expected_arrival: expected ISO-formatted datetime.") from exc
            previous_expected_arrival = require_naive_datetime(parsed_arrival, "previous_expected_arrival")
        new_expected_arrival = None
        if payload["new_expected_arrival"] is not None:
            arrival_text = require_str(payload["new_expected_arrival"], "new_expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("new_expected_arrival: expected ISO-formatted datetime.") from exc
            new_expected_arrival = require_naive_datetime(parsed_arrival, "new_expected_arrival")
        reason = PackageDetachmentReason(require_str(payload["reason"], "reason"))

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
