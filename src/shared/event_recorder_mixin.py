from src.shared.event import Event


class EventRecorderMixin[E: Event]:
    """Generic mixin providing event recording for aggregates and services."""

    __slots__ = ()

    _pending_events: list[E]

    def _record_event(self, event: E) -> None:
        """Record a pending event.

        Args:
            event: The event to record.
        """
        self._pending_events.append(event)

    @property
    def pending_events(self) -> tuple[E, ...]:
        """Return all pending events as an immutable tuple."""
        return tuple(self._pending_events)

    def clear_events(self) -> None:
        """Clear all pending events."""
        self._pending_events.clear()

    def event_checkpoint(self) -> int:
        """Return the current event count as a restore point."""
        return len(self._pending_events)

    def restore_event_checkpoint(self, checkpoint: int) -> None:
        """Truncate pending events back to a previous checkpoint.

        Args:
            checkpoint: Index returned by a prior call to event_checkpoint.

        Raises:
            ValueError: If checkpoint is out of range or is a bool.
        """
        if isinstance(checkpoint, bool) or not 0 <= checkpoint <= len(self._pending_events):
            raise ValueError("Invalid checkpoint value.")
        del self._pending_events[checkpoint:]
