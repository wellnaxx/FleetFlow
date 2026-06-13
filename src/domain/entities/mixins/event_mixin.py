from src.domain.events.base import DomainEvent


class EventRecorderMixin:
    """Mixin class that provides event recording functionality for entities."""

    __slots__ = ()

    _pending_events: list[DomainEvent]

    def _record_event(self, event: DomainEvent) -> None:
        """Record a domain event.

        Args:
            event (DomainEvent): The domain event to be recorded.
        """
        self._pending_events.append(event)

    @property
    def pending_events(self) -> tuple[DomainEvent, ...]:
        """Get the pending domain events.

        Returns:
            A tuple of pending domain events.
        """
        return tuple(self._pending_events)
    
    def clear_events(self) -> None:
        """Clear all pending domain events."""
        self._pending_events.clear()

    def event_checkpoint(self) -> int:
        """Get the current checkpoint for pending events.

        Returns:
            An integer representing the current checkpoint for pending events.
        """
        return len(self._pending_events)
    
    def restore_event_checkpoint(self, checkpoint: int) -> None:
        """Restore the pending events to a specific checkpoint.

        Args:
            checkpoint (int): The checkpoint to restore to.
        """
        if isinstance(checkpoint, bool) or not 0 <= checkpoint <= len(self._pending_events):
            raise ValueError("Invalid checkpoint value.")
        
        del self._pending_events[checkpoint:]
