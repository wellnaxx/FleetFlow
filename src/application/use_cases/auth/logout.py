"""Use case for ending the current auth session."""

import logging

from src.application.services.auth_service import AuthService
from src.application.use_cases.base.base_use_case import BaseUseCase

logger = logging.getLogger(__name__)


class LogoutUseCase(BaseUseCase[None]):
    """Terminate the current authentication session."""

    def __init__(self, auth: AuthService) -> None:
        """Initialize the use case.

        Args:
            auth: Authentication service containing the current session.
        """
        self._auth = auth

    def execute(self) -> None:
        """Log out the current user."""
        current_user = self._auth.current_user
        self._auth.logout()
        if current_user is not None:
            logger.info("Logged out user_id=%d.", current_user.user_id)
        else:
            logger.debug("Logout requested with no active user.")
