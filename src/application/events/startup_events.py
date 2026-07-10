"""Application events describing startup workflows."""

from dataclasses import dataclass
from typing import ClassVar

from src.application.events.base import ApplicationEvent


@dataclass(frozen=True, slots=True, kw_only=True)
class FleetSeeded(ApplicationEvent):
    """Event recorded when the truck fleet is seeded at startup.

    Attributes:
        seeded_truck_ids: Stable identifiers of every truck created by the
            seeding workflow.
        backend: Persistence backend into which the fleet was seeded.
    """

    event_version: ClassVar[int] = 2

    seeded_truck_ids: tuple[int, ...]
    backend: str

    @property
    def truck_count(self) -> int:
        """Return the number of seeded trucks from the identifier snapshot."""
        return len(self.seeded_truck_ids)
