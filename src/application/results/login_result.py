from dataclasses import dataclass

from src.application.models.user_record import UserRecord
from src.domain.entities.users.user import User


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Authenticated user data needed by driving adapters.

    Attributes:
        record: Persisted user record used for token creation and response data.
        user: Runtime user entity used by CLI/session-facing adapters.
    """

    record: UserRecord
    user: User
