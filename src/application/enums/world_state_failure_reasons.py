"""Operation-level reasons for failed world-state workflows."""

from enum import StrEnum


class WorldStateFailureReason(StrEnum):
    """Reasons an import or export operation did not complete.

    `UNSUPPORTED_SCHEMA` means the workflow rejected a snapshot because its
    schema cannot be processed. It describes the operation outcome; use
    `WorldStateCorruptionReason.UNSUPPORTED_SCHEMA` when classifying the
    persisted snapshot defect itself.
    """

    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    CORRUPT_SNAPSHOT = "CORRUPT_SNAPSHOT"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"
    PERSISTENCE_FAILURE = "PERSISTENCE_FAILURE"
    RUNTIME_SWAP_FAILURE = "RUNTIME_SWAP_FAILURE"
