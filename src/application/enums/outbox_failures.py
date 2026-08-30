"""Failure categories for transactional-outbox processing."""

from enum import StrEnum


class OutboxFailureCategory(StrEnum):
    """Classify the processing stage responsible for an outbox failure.

    The category is machine-readable state used for filtering and operational
    policy. Detailed diagnostics remain in the message's free-text
    ``last_error`` field.

    Attributes:
        SERIALIZATION: The stored event could not be encoded for publication.
        DESERIALIZATION: Stored event data could not be reconstructed.
        PUBLICATION: Delivery to the configured event publisher failed.
        HANDLER: A synchronous downstream event handler failed.
        UNKNOWN: The failure could not be assigned a more specific category.
    """

    SERIALIZATION = "serialization"
    DESERIALIZATION = "deserialization"
    PUBLICATION = "publication"
    HANDLER = "handler"
    UNKNOWN = "unknown"
