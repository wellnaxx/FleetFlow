"""Event publication envelopes and authenticated actor metadata."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.application.enums.event_sources import EventSource
from src.shared.event import Event


@dataclass(frozen=True, slots=True)
class EventActor:
    """Authenticated user responsible for an event-producing workflow.

    Attributes:
        user_id: Positive persisted identifier of the authenticated user.
        username: Normalized lowercase username of the authenticated user.
    """

    user_id: int
    username: str

    def __post_init__(self) -> None:
        """Validate and normalize actor identity metadata."""
        self._validate_user_id(self.user_id)
        normalized_username = self._normalize_username(self.username)
        object.__setattr__(self, "username", normalized_username)

    @staticmethod
    def _validate_user_id(value: object) -> None:
        if not isinstance(value, int) or isinstance(value, bool) or value < 1:
            raise ValueError("user_id must be a positive integer.")

    @staticmethod
    def _normalize_username(value: object) -> str:
        if not isinstance(value, str):
            raise TypeError("username must be a non-empty string.")

        normalized_username = value.strip().lower()
        if not normalized_username:
            raise ValueError("username must be a non-empty string.")
        return normalized_username


@dataclass(frozen=True, slots=True, kw_only=True)
class EventEnvelope[E: Event]:
    """Capture immutable execution and causality context for one event.

    Attributes:
        event: Domain or application event being published.
        source: Execution origin that produced the event.
        correlation_id: Identifier shared by one request, command, or workflow.
        actor: Authenticated user that initiated the workflow, if any.
        causation_id: Identifier of the event or command that directly caused
            this event, when applicable.
        envelope_id: Unique identifier for this publication envelope.
    """

    event: E
    source: EventSource
    correlation_id: UUID
    actor: EventActor | None = None
    causation_id: UUID | None = None
    envelope_id: UUID = field(default_factory=uuid4)
