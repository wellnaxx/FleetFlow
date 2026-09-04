"""Failures raised by outbox codec registration and resolution."""


class EventCodecRegistryError(RuntimeError):
    """Base class for outbox codec configuration and lookup defects."""


class DuplicateEventCodecError(EventCodecRegistryError):
    """Raised when a codec event class or persisted identity is occupied."""


class EventCodecNotFoundError(EventCodecRegistryError):
    """Raised when no codec is registered for an event or persisted identity."""


class EventCodecTypeMismatchError(EventCodecRegistryError, TypeError):
    """Raised when a codec receives or reconstructs the wrong event type."""
