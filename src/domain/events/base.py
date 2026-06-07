"""Base type for events produced by the domain model."""

from dataclasses import dataclass

from src.shared.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class DomainEvent(Event):
    """Marker base for facts produced by the domain model."""
