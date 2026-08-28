"""Base contract for permission-protected, event-aware use cases."""

from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.base_use_case import BaseUseCase
from src.application.use_cases.base.event_mixin import ApplicationEventRecorderMixin


class AuthorizedUseCase[T](BaseUseCase[T], ApplicationEventRecorderMixin):
    """Base for permission-protected use cases that record application events.

    Permission decorators record ``AuthorizationDenied`` through the active
    event-recorder scope when a message executor owns publication. Intentional
    unscoped execution, primarily in focused unit tests, retains events on the
    use-case instance. Subclasses must call ``super().__init__`` with their
    authorization service.
    """

    def __init__(self, authz: AuthorizationService) -> None:
        """Initialize authorization state and an empty pending-event buffer.

        Args:
            authz: Authorization service containing the current principal.
        """
        self._authz = authz
        self._pending_events = []

    @property
    def authz(self) -> AuthorizationService:
        """Return the authorization service used by permission decorators."""
        return self._authz
