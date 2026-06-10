import uuid
from dataclasses import dataclass, field

from src.application.enums.event_sources import EventSource
from src.shared.event import Event


@dataclass(frozen=True, slots=True)
class EventActor:
    """Represents the actor responsible for triggering an event."""

    user_id: int
    username: str

    def __post_init__(self) -> None:
        if isinstance(self.user_id, bool) or self.user_id < 1:
            raise ValueError("user_id must be a positive integer.")

        normalized_username = self.username.strip().lower()
        if not normalized_username:
            raise ValueError("username must be a non-empty string.")

        object.__setattr__(self, "username", normalized_username)


@dataclass(frozen=True, slots=True, kw_only=True)
class EventEnvelope[E: Event]:
    """Wraps any event with actor and transport context."""

    event: E
    source: EventSource
    actor: EventActor | None = None

    correlation_id: uuid.UUID
    """Groups all events from the same request or session."""

    causation_id: uuid.UUID | None = None
    """ID of the event or command that directly caused this event."""

    envelope_id: uuid.UUID = field(default_factory=uuid.uuid4)
