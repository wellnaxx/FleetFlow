from dataclasses import dataclass

from src.domain.enums.auth import Role


@dataclass(frozen=True, slots=True, kw_only=True)
class CurrentUserPrincipal:
    """Application-level identity for the currently authenticated actor.

    The principal is distinct from the persisted ``UserRecord`` and from the
    domain user entity hierarchy. It carries only the identity and role data
    needed by authorization, event context, and session-aware use cases.
    """

    user_id: int
    username: str
    name: str
    email: str
    phone_number: str
    role: Role
