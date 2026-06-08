"""Base type for events produced by application workflows."""

from dataclasses import dataclass

from src.shared.event import Event


@dataclass(frozen=True, slots=True, kw_only=True)
class ApplicationEvent(Event):
    """Marker base for facts produced by application workflows."""
