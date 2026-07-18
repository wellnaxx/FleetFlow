"""Event publication envelopes and authenticated actor metadata."""

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.application.enums.event_sources import EventSource
from src.shared.event import Event
from src.shared.validation import require_non_empty_str, require_positive_int


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
        try:
            require_positive_int(value, "user_id")
        except (TypeError, ValueError) as exc:
            raise ValueError("user_id must be a positive integer.") from exc

    @staticmethod
    def _normalize_username(value: object) -> str:
        try:
            return require_non_empty_str(value, "username").lower()
        except TypeError as exc:
            raise TypeError("username must be a non-empty string.") from exc
        except ValueError as exc:
            raise ValueError("username must be a non-empty string.") from exc


@dataclass(frozen=True, slots=True, kw_only=True)
class EventEnvelope[E: Event]:
    """Capture immutable execution and causality context for one event.

    The event payload is stored privately and exposed through a read-only
    property. This lets PEP 695 variance inference treat ``EventEnvelope`` as
    covariant in ``E``: an ``EventEnvelope[RouteCreated]`` can be published
    where an ``EventEnvelope[Event]`` is expected.

    Attributes:
        event: Domain or application event being published.
        source: Execution origin that produced the event.
        correlation_id: Identifier shared by one request, command, or workflow.
        actor: Authenticated user that initiated the workflow, if any.
        causation_id: Identifier of the event or command that directly caused
            this event, when applicable.
        envelope_id: Unique identifier for this publication envelope.
    """

    _event: E
    source: EventSource
    correlation_id: UUID
    actor: EventActor | None = None
    causation_id: UUID | None = None
    envelope_id: UUID = field(default_factory=uuid4)

    def __init__(
        self,
        *,
        event: E,
        source: EventSource,
        correlation_id: UUID,
        actor: EventActor | None = None,
        causation_id: UUID | None = None,
        envelope_id: UUID | None = None,
    ) -> None:
        """Create an immutable envelope while preserving a public event API.

        Args:
            event: Domain or application event to publish.
            source: Execution origin that produced the event.
            correlation_id: Identifier shared by the producing workflow.
            actor: Authenticated initiator of the workflow, when present.
            causation_id: Identifier of the direct event or command cause.
            envelope_id: Explicit publication identifier. A new UUID is
                generated when omitted.
        """
        object.__setattr__(self, "_event", event)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "correlation_id", correlation_id)
        object.__setattr__(self, "actor", actor)
        object.__setattr__(self, "causation_id", causation_id)
        object.__setattr__(self, "envelope_id", envelope_id if envelope_id is not None else uuid4())

    @property
    def event(self) -> E:
        """Return the immutable domain or application event payload."""
        return self._event
