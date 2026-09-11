"""Outbox payload codecs for package lifecycle events.

Payloads contain event-specific data only. Universal event metadata is supplied
separately on decoding; business timestamps remain naive app-local values.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.enums.item_status import ItemStatus
from src.domain.events.package_events import PackageCreated, PackageRemoved
from src.domain.value_objects.location_code import LocationCode
from src.shared.json_serialization import optional_isoformat
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import (
    require_naive_datetime,
    require_optional_positive_int,
    require_positive_finite_float,
    require_positive_int,
    require_str,
)


class PackageCreatedEventPayloadCodec(EventPayloadCodec[PackageCreated]):
    """Encode and decode the version-2 package-creation snapshot.

    All eight payload keys are required, including nullable expected_arrival.
    IDs are positive integers, weight is a finite positive number, locations
    use LocationCode normalization, and initial_status uses an ItemStatus value.
    Encoding trusts typed event fields; decoding validates serialized data
    without reapplying package-creation policies to historical snapshots.
    """

    @property
    def event_class(self) -> type[PackageCreated]:
        """Return the concrete package-created event class."""
        return PackageCreated

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``package_created``."""
        return "package_created"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: PackageCreated) -> JSONObject:
        """Serialize a package-creation snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed snapshot fields.

        Returns:
            Integer IDs, string locations and status, numeric weight, and an
            ISO-formatted arrival timestamp or null. Event and envelope
            metadata are excluded; timestamp microseconds are preserved.
        """
        return {
            "package_id": event.package_id,
            "customer_id": event.customer_id,
            "start_location": str(event.start_location),
            "end_location": str(event.end_location),
            "weight": event.weight,
            "initial_status": event.initial_status.value,
            "initial_location": str(event.initial_location),
            "expected_arrival": optional_isoformat(event.expected_arrival),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> PackageCreated:
        """Validate the payload and reconstruct its typed event snapshot.

        Args:
            payload: JSON object with exactly the eight version-2 snapshot keys.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event with typed locations, status, and optional arrival.
            The input payload is neither mutated nor retained.

        Raises:
            TypeError: If a payload field or metadata has an invalid runtime
                type. Booleans are not accepted as IDs or weight.
            ValueError: If keys are missing or unexpected, IDs or weight are
                non-positive, weight is non-finite, status is unknown, arrival
                text is invalid, or a timestamp uses the wrong time domain.
            DomainValidationError: If a location is blank after normalization.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "package_id",
            "customer_id",
            "start_location",
            "end_location",
            "weight",
            "initial_status",
            "initial_location",
            "expected_arrival",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        package_id = require_positive_int(payload["package_id"], "package_id")
        customer_id = require_positive_int(payload["customer_id"], "customer_id")
        start_location = LocationCode(require_str(payload["start_location"], "start_location"))
        end_location = LocationCode(require_str(payload["end_location"], "end_location"))
        weight = require_positive_finite_float(payload["weight"], "weight")
        initial_status = ItemStatus(require_str(payload["initial_status"], "initial_status"))
        initial_location = LocationCode(require_str(payload["initial_location"], "initial_location"))
        expected_arrival = None
        if payload["expected_arrival"] is not None:
            arrival_text = require_str(payload["expected_arrival"], "expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("expected_arrival: expected ISO-formatted datetime.") from exc
            expected_arrival = require_naive_datetime(parsed_arrival, "expected_arrival")

        return PackageCreated(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            package_id=package_id,
            customer_id=customer_id,
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            initial_status=initial_status,
            initial_location=initial_location,
            expected_arrival=expected_arrival,
        )


class PackageRemovedEventPayloadCodec(EventPayloadCodec[PackageRemoved]):
    """Encode and decode the version-2 snapshot captured before removal.

    All nine payload keys are required. previous_route_id and
    previous_expected_arrival may independently be null; previous_location
    must contain a non-blank location. IDs are positive integers, weight is a
    finite positive number, and previous_status uses an ItemStatus value.
    Encoding trusts typed event fields. Decoding validates the snapshot without
    looking up current entities or reapplying removal eligibility rules.
    """

    @property
    def event_class(self) -> type[PackageRemoved]:
        """Return the concrete package-removed event class."""
        return PackageRemoved

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``package_removed``."""
        return "package_removed"

    @property
    def event_version(self) -> int:
        """Return the explicit supported payload contract version."""
        return 2

    def encode(self, event: PackageRemoved) -> JSONObject:
        """Serialize the pre-removal snapshot into a fresh JSON object.

        Args:
            event: Version-2 event with correctly typed snapshot fields.

        Returns:
            Integer IDs, string locations and status, numeric weight, and an
            ISO-formatted previous arrival with microseconds preserved. Missing
            route and arrival values become JSON null. Event and envelope
            metadata are excluded.
        """
        return {
            "package_id": event.package_id,
            "customer_id": event.customer_id,
            "previous_route_id": event.previous_route_id,
            "previous_status": event.previous_status.value,
            "previous_location": str(event.previous_location),
            "start_location": str(event.start_location),
            "end_location": str(event.end_location),
            "weight": event.weight,
            "previous_expected_arrival": optional_isoformat(event.previous_expected_arrival),
        }

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> PackageRemoved:
        """Validate a removal payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly the nine version-2 keys,
                including both nullable fields even when their values are null.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new event containing typed locations, status, and optional naive
            arrival. The input payload is neither mutated nor retained.

        Raises:
            TypeError: If payload fields or metadata have invalid runtime
                types. Booleans are not accepted as IDs or weight, and a
                non-null arrival must be a string rather than a datetime.
            ValueError: If keys are missing or unexpected, IDs or weight are
                non-positive, weight is non-finite, status is unknown, arrival
                text is invalid, or a timestamp uses the wrong time domain.
            DomainValidationError: If any location is blank after normalization.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset([
            "package_id",
            "customer_id",
            "previous_route_id",
            "previous_status",
            "previous_location",
            "start_location",
            "end_location",
            "weight",
            "previous_expected_arrival",
        ])

        require_json_object_keys(payload, expected_payload_keys)

        package_id = require_positive_int(payload["package_id"], "package_id")
        customer_id = require_positive_int(payload["customer_id"], "customer_id")
        previous_route_id = require_optional_positive_int(payload["previous_route_id"], "previous_route_id")
        previous_status = ItemStatus(require_str(payload["previous_status"], "previous_status"))
        previous_location = LocationCode(require_str(payload["previous_location"], "previous_location"))
        start_location = LocationCode(require_str(payload["start_location"], "start_location"))
        end_location = LocationCode(require_str(payload["end_location"], "end_location"))
        weight = require_positive_finite_float(payload["weight"], "weight")
        previous_expected_arrival = None
        if payload["previous_expected_arrival"] is not None:
            arrival_text = require_str(payload["previous_expected_arrival"], "previous_expected_arrival")
            try:
                parsed_arrival = datetime.fromisoformat(arrival_text)
            except ValueError as exc:
                raise ValueError("previous_expected_arrival: expected ISO-formatted datetime.") from exc
            previous_expected_arrival = require_naive_datetime(parsed_arrival, "previous_expected_arrival")

        return PackageRemoved(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            package_id=package_id,
            customer_id=customer_id,
            previous_route_id=previous_route_id,
            previous_status=previous_status,
            previous_location=previous_location,
            start_location=start_location,
            end_location=end_location,
            weight=weight,
            previous_expected_arrival=previous_expected_arrival,
        )
