"""Concrete outbox payload codecs for customer lifecycle events.

Only event-specific data is encoded. Universal event metadata is supplied
separately during decoding; actor and envelope metadata stays in the outbox
message's dedicated fields.
"""

from datetime import datetime
from typing import Final
from uuid import UUID

from src.application.eventing.outbox.codec import EventPayloadCodec
from src.domain.events.customer_events import CustomerCreated
from src.shared.json_types import JSONObject
from src.shared.json_validation import require_json_object_keys
from src.shared.validation import require_positive_int


class CustomerCreatedEventPayloadCodec(EventPayloadCodec[CustomerCreated]):
    """Encode and decode version-1 customer-creation payloads.

    Exactly ``customer_id`` is required and must be a positive integer,
    excluding booleans. Customer contact details are absent from this event's
    contract. Encoding expects correctly typed event fields; decoding validates
    the payload and delegates universal metadata validation to the event
    constructor.
    """

    @property
    def event_class(self) -> type[CustomerCreated]:
        """Return the concrete customer-created event class."""
        return CustomerCreated

    @property
    def event_type(self) -> str:
        """Return the stable persisted identity ``customer_created``."""
        return "customer_created"

    @property
    def event_version(self) -> int:
        """Return the explicit payload contract version supported here."""
        return 1

    def encode(self, event: CustomerCreated) -> JSONObject:
        """Serialize the created customer's identity into a fresh JSON object.

        Args:
            event: Version-1 customer-created event to serialize.

        Returns:
            An object containing the integer customer ID. Contact details and
            event and envelope metadata are excluded.
        """
        return {"customer_id": event.customer_id}

    def decode(
        self,
        payload: JSONObject,
        *,
        event_id: UUID,
        occurred_at: datetime,
        recorded_at: datetime,
    ) -> CustomerCreated:
        """Validate a version-1 payload and restore its original event metadata.

        Args:
            payload: JSON object containing exactly customer_id.
            event_id: Original event UUID.
            occurred_at: Original naive app-local business timestamp.
            recorded_at: Original UTC-aware recording timestamp.

        Returns:
            A new customer-created event with the supplied metadata. The input
            payload is not mutated or retained.

        Raises:
            TypeError: If customer_id or metadata has an invalid runtime type,
                including a null, boolean, string, or float customer ID.
            ValueError: If keys are missing or unexpected, customer_id is not
                positive, or timestamps use the wrong time domain.
        """
        expected_payload_keys: Final[frozenset[str]] = frozenset(["customer_id"])

        require_json_object_keys(payload, expected_payload_keys)

        customer_id = require_positive_int(payload["customer_id"], "customer_id")

        return CustomerCreated(
            event_id=event_id,
            occurred_at=occurred_at,
            recorded_at=recorded_at,
            customer_id=customer_id,
        )
