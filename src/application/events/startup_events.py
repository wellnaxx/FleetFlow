"""Application events describing startup workflows."""

from dataclasses import dataclass

from src.application.events.base import ApplicationEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class FleetSeeded(ApplicationEvent):
    """Event recorded when the truck fleet is seeded at startup."""

    truck_count: int
    backend: str
