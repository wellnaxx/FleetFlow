"""Failures owned by command/query registration and dispatch infrastructure.

Messaging errors indicate programming or composition defects rather than
expected application outcomes. Buses must allow errors raised by registered
handlers to propagate unchanged instead of wrapping them in this hierarchy.
"""


class MessageBusError(RuntimeError):
    """Base class for message registration and routing defects."""


class DuplicateMessageHandlerError(MessageBusError):
    """Raised when composition registers a handler for an occupied key name."""


class MessageHandlerNotFoundError(MessageBusError):
    """Raised when dispatch cannot resolve the supplied routing-key name."""


class MessageTypeMismatchError(MessageBusError, TypeError):
    """Raised when a message or registration type disagrees with its key."""
