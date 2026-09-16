"""Outbox payload codecs for application-level reconciliation events.

Payloads retain event-specific correction snapshots. Universal event metadata
is supplied separately when decoding; schedule timestamps remain naive app-local.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.enums.package_reconciliation_reasons import PackageReconciliationReason
from src.application.enums.route_reconciliation_reasons import RouteReconciliationReason
from src.application.eventing.outbox.codec import EventPayloadCodec
from src.application.events.reconciliation_events import PackageStateReconciled, RouteStateReconciled
from src.domain.enums.item_status import ItemStatus
from src.domain.enums.route_status import RouteStatus
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


class RouteStateReconciledEventPayloadCodec(EventPayloadCodec[RouteStateReconciled]):
    """Encode and decode the version-1 route status correction snapshot.

    All six payload keys are required. Departure and expected completion may
    independently be null; route_id must be a positive integer. Statuses and
    the single reconciliation reason use enum values, not member names.
    Encoding trusts typed event fields. Decoding validates representations
    without rebuilding schedules or reapplying reconciliation policies.
    """

    @property
    def event_class(self) -> type[RouteStateReconciled]:
        """Return the concrete route-state-reconciled application event class."""
        return RouteStateReconciled

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``route_state_reconciled``."""
        return "route_state_reconciled"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 1

    def encode(self, event: RouteStateReconciled) -> JSONObject:
        """Serialize the route correction into a fresh JSON object.

        Args:
            event: Version-1 event with correctly typed correction fields.

        Returns:
            Integer route ID, string before/after statuses and reason, and
            ISO-formatted schedule timestamps or JSON null. Microseconds are
            preserved; event and envelope metadata are excluded.
        """
        return {
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "departure_time": optional_isoformat(event.departure_time),
            "expected_completion_time": optional_isoformat(event.expected_completion_time),
            "reason": event.reason.value,
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> RouteStateReconciled:
        """Validate a correction payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the six version-1 keys.
                Both timestamp keys must exist even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event preserving the route ID, typed statuses and reason,
            and optional naive schedule timestamps. The input payload is neither
            mutated nor retained.

        Raises:
            TypeError: If a field or metadata has an invalid runtime type.
                Booleans are not valid IDs, and non-null schedule timestamps
                must be strings rather than datetime objects.
            ValueError: If keys are missing or unexpected, route_id is
                non-positive, a status or reason is unknown, timestamp text
                is invalid, or timestamps use the wrong time domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "route_id",
            "previous_status",
            "new_status",
            "departure_time",
            "expected_completion_time",
            "reason",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        route_id = require_positive_int(payload["route_id"], "route_id")
        previous_status = RouteStatus(require_str(payload["previous_status"], "previous_status"))
        new_status = RouteStatus(require_str(payload["new_status"], "new_status"))
        departure_time = None
        if payload["departure_time"] is not None:
            departure_text = require_str(payload["departure_time"], "departure_time")
            try:
                parsed_departure = datetime.fromisoformat(departure_text)
            except ValueError as exc:
                raise ValueError("departure_time: expected ISO-formatted datetime.") from exc
            departure_time = require_naive_datetime(parsed_departure, "departure_time")
        expected_completion_time = None
        if payload["expected_completion_time"] is not None:
            completion_text = require_str(payload["expected_completion_time"], "expected_completion_time")
            try:
                parsed_completion = datetime.fromisoformat(completion_text)
            except ValueError as exc:
                raise ValueError("expected_completion_time: expected ISO-formatted datetime.") from exc
            expected_completion_time = require_naive_datetime(parsed_completion, "expected_completion_time")
        reason = RouteReconciliationReason(require_str(payload["reason"], "reason"))

        return RouteStateReconciled(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            route_id=route_id,
            previous_status=previous_status,
            new_status=new_status,
            departure_time=departure_time,
            expected_completion_time=expected_completion_time,
            reason=reason,
        )


class PackageStateReconciledEventPayloadCodec(EventPayloadCodec[PackageStateReconciled]):
    """Encode and decode the version-1 package correction snapshot.

    All eleven keys are required. route_id and the four schedule timestamps may
    independently be null; package_id must be a positive integer. Statuses and
    reasons use enum values, and locations use LocationCode normalization.
    Reasons retain their order and must be non-empty and unique, as enforced
    by the event constructor. Encoding trusts typed event fields; decoding does
    not recalculate schedules or reapply reconciliation policies.
    """

    @property
    def event_class(self) -> type[PackageStateReconciled]:
        """Return the concrete package-state-reconciled application event class."""
        return PackageStateReconciled

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``package_state_reconciled``."""
        return "package_state_reconciled"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 1

    def encode(self, event: PackageStateReconciled) -> JSONObject:
        """Serialize the package correction into a fresh JSON object.

        Args:
            event: Version-1 event with correctly typed correction fields.

        Returns:
            Integer IDs, string before/after statuses and locations, an ordered
            fresh list of reason values, and ISO-formatted timestamps with
            microseconds preserved. Absent route and timestamps become JSON
            null. Event and envelope metadata are excluded.
        """
        return {
            "package_id": event.package_id,
            "route_id": event.route_id,
            "previous_status": event.previous_status.value,
            "new_status": event.new_status.value,
            "previous_location": str(event.previous_location),
            "new_location": str(event.new_location),
            "previous_expected_arrival": optional_isoformat(event.previous_expected_arrival),
            "new_expected_arrival": optional_isoformat(event.new_expected_arrival),
            "scheduled_pickup_time": optional_isoformat(event.scheduled_pickup_time),
            "scheduled_delivery_time": optional_isoformat(event.scheduled_delivery_time),
            "reasons": [reason.value for reason in event.reasons],
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> PackageStateReconciled:
        """Validate a package correction and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the eleven version-1 keys.
                Nullable fields must exist even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with typed statuses, locations, optional naive schedule
            timestamps, and a tuple of unique reasons in payload order. The
            input payload and its reasons list are neither mutated nor retained.

        Raises:
            TypeError: If a field or metadata has an invalid runtime type.
                Booleans are not valid IDs, reasons must be a list of strings,
                and non-null timestamps must be strings rather than datetimes.
            ValueError: If keys are missing or unexpected, an ID is non-positive,
                a status or reason is unknown, reasons are empty or duplicated,
                timestamp text is invalid, or timestamps use the wrong time domain.
            DomainValidationError: If either location is blank after normalization.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "package_id",
            "route_id",
            "previous_status",
            "new_status",
            "previous_location",
            "new_location",
            "previous_expected_arrival",
            "new_expected_arrival",
            "scheduled_pickup_time",
            "scheduled_delivery_time",
            "reasons",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        package_id = require_positive_int(payload["package_id"], "package_id")
        route_id = require_optional_positive_int(payload["route_id"], "route_id")
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
        scheduled_pickup_time = None
        if payload["scheduled_pickup_time"] is not None:
            pickup_text = require_str(payload["scheduled_pickup_time"], "scheduled_pickup_time")
            try:
                parsed_pickup = datetime.fromisoformat(pickup_text)
            except ValueError as exc:
                raise ValueError("scheduled_pickup_time: expected ISO-formatted datetime.") from exc
            scheduled_pickup_time = require_naive_datetime(parsed_pickup, "scheduled_pickup_time")
        scheduled_delivery_time = None
        if payload["scheduled_delivery_time"] is not None:
            delivery_text = require_str(payload["scheduled_delivery_time"], "scheduled_delivery_time")
            try:
                parsed_delivery = datetime.fromisoformat(delivery_text)
            except ValueError as exc:
                raise ValueError("scheduled_delivery_time: expected ISO-formatted datetime.") from exc
            scheduled_delivery_time = require_naive_datetime(parsed_delivery, "scheduled_delivery_time")
        raw_reasons = require_list(payload["reasons"], "reasons")
        reasons: list[PackageReconciliationReason] = []
        for index, item in enumerate(raw_reasons):
            field_name = f"reasons[{index}]"
            name = require_str(item, field_name)
            reasons.append(PackageReconciliationReason(name))

        return PackageStateReconciled(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            package_id=package_id,
            route_id=route_id,
            previous_status=previous_status,
            new_status=new_status,
            previous_location=previous_location,
            new_location=new_location,
            previous_expected_arrival=previous_expected_arrival,
            new_expected_arrival=new_expected_arrival,
            scheduled_pickup_time=scheduled_pickup_time,
            scheduled_delivery_time=scheduled_delivery_time,
            reasons=tuple(reasons),
        )
