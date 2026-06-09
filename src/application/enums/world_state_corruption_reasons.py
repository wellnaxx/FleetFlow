"""Data-level reasons a persisted world-state snapshot is invalid."""

from enum import StrEnum


class WorldStateCorruptionReason(StrEnum):
    """Classifications of defects detected in persisted snapshot data.

    `UNSUPPORTED_SCHEMA` identifies an incompatible schema in the snapshot
    itself. Use `WorldStateFailureReason.UNSUPPORTED_SCHEMA` when recording
    the resulting import or restore operation failure.
    """

    MALFORMED_DOCUMENT = "MALFORMED_DOCUMENT"
    UNSUPPORTED_SCHEMA = "UNSUPPORTED_SCHEMA"
    INVALID_REFERENCES = "INVALID_REFERENCES"
    INVARIANT_VIOLATION = "INVARIANT_VIOLATION"
