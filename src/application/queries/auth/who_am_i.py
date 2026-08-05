"""Query contract for inspecting the current authentication principal."""

from dataclasses import dataclass
from typing import Final

from src.application.messaging.query import Query, QueryKey
from src.application.models.current_user_principal import CurrentUserPrincipal


@dataclass(frozen=True, slots=True, kw_only=True)
class WhoAmIQuery(Query):
    """Request the current principal from authentication context.

    The query has no fields because principal identity is trusted contextual
    state and must not be supplied by a caller. A successful dispatch may
    still return ``None`` when no user is authenticated.
    """


WHO_AM_I: Final[QueryKey[WhoAmIQuery, CurrentUserPrincipal | None]] = QueryKey(
    name="who_am_i",
    query_type=WhoAmIQuery,
)
