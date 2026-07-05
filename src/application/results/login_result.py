from dataclasses import dataclass

from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.models.user_record import UserRecord


@dataclass(frozen=True, slots=True)
class LoginResult:
    """Authenticated user data needed by driving adapters.

    Attributes:
        record: Persisted user record used for token creation and response data.
        principal: Current authenticated principal used by session-aware adapters.
    """

    record: UserRecord
    principal: CurrentUserPrincipal
