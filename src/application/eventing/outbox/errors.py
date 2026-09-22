"""Failures raised by outbox codec configuration, lookup, and contract checks."""


class EventCodecRegistryError(RuntimeError):
    """Base class for outbox codec configuration, lookup, and contract defects."""


class DuplicateEventCodecError(EventCodecRegistryError):
    """Raised when a codec event class or persisted identity is occupied."""


class EventCodecNotFoundError(EventCodecRegistryError):
    """Raised when no codec is registered for an event or persisted identity."""


class EventCodecTypeMismatchError(EventCodecRegistryError, TypeError):
    """Raised when a codec receives or reconstructs the wrong event type."""


class EventCodecVersionMismatchError(EventCodecRegistryError):
    """Raised when a codec version is incompatible with its registration role."""


class EventCodecContractError(EventCodecRegistryError):
    """Raised when serialization loses event data or changes supplied metadata."""
