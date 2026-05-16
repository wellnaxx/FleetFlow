from src.application.services.authorization_service import AuthorizationService
from src.application.use_cases.base.base_use_case import BaseUseCase


class AuthorizedUseCase[T](BaseUseCase[T]):
    """Base for use cases that enforce permissions through @requires or @requires_all.

    Subclasses must call super().__init__(authz).
    """

    def __init__(self, authz: AuthorizationService) -> None:
        self._authz = authz

    @property
    def authz(self) -> AuthorizationService:
        """Authorization service used by permission decorators."""
        return self._authz
