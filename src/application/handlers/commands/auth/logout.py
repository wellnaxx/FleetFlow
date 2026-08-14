"""Command handler for terminating the current session."""

from src.application.commands.auth.logout import LogoutCommand
from src.application.use_cases.auth.logout import LogoutUseCase


class LogoutCommandHandler:
    """Adapt a context-driven logout command to the logout workflow."""

    def __init__(self, use_case: LogoutUseCase) -> None:
        """Initialize the handler.

        Args:
            use_case: Session-termination workflow to invoke.
        """
        self._use_case = use_case

    def execute(self, command: LogoutCommand) -> None:
        """Terminate the authenticated session represented by context.

        Args:
            command: Fieldless message selecting the logout workflow.

        Raises:
            Exception: Propagates authorization, persistence, and other
                failures raised by the use case.
        """
        del command
        self._use_case.execute()
