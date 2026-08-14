"""Query handler for current-principal inspection."""

from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.queries.auth.who_am_i import WhoAmIQuery
from src.application.use_cases.auth.who_am_i import WhoAmIUseCase


class WhoAmIQueryHandler:
    """Delegate a context-driven principal query to its workflow."""

    def __init__(self, use_case: WhoAmIUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Current-principal workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, query: WhoAmIQuery) -> CurrentUserPrincipal | None:
        """Return the current principal, if one is authenticated.

        Args:
            query: Fieldless message selecting the principal workflow.

        Returns:
            Current principal, or ``None`` when unauthenticated.

        Raises:
            Exception: Propagates failures raised by the use case.
        """
        del query
        return self._use_case.execute()
