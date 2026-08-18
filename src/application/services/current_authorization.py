"""Context-local authorization identity for one application execution."""

from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass

from src.application.models.current_user_principal import CurrentUserPrincipal


@dataclass(frozen=True, slots=True)
class AuthorizationContext:
    """Trusted principal bound to the current execution.

    A context containing ``None`` represents an explicitly unauthenticated
    execution. No bound context means consumers should use their session-level
    authorization fallback instead.

    Attributes:
        current_user: Authenticated principal, or ``None`` for an anonymous
            execution.
    """

    current_user: CurrentUserPrincipal | None


_current_authorization_context: ContextVar[AuthorizationContext | None] = ContextVar(
    "current_authorization_context", default=None
)


def get_authorization_context() -> AuthorizationContext:
    """Return the authorization context bound to this execution.

    Returns:
        Currently bound authorization context.

    Raises:
        RuntimeError: If no authorization context is bound.
    """
    context = _current_authorization_context.get()
    if context is None:
        raise RuntimeError("No authorization context is bound.")
    return context


def get_optional_authorization_context() -> AuthorizationContext | None:
    """Return the current context, or ``None`` when no context is bound."""
    return _current_authorization_context.get()


@contextmanager
def bind_authorization_context(current_user: CurrentUserPrincipal | None) -> Generator[AuthorizationContext]:
    """Bind a trusted principal and restore the prior context afterward.

    Nested bindings restore their predecessor even when execution raises.
    ``ContextVar`` storage also isolates concurrent asynchronous request tasks.

    Args:
        current_user: Trusted principal to expose, or ``None`` to bind an
            explicitly unauthenticated execution.

    Yields:
        Newly bound immutable authorization context.
    """
    context = AuthorizationContext(current_user=current_user)
    token = _current_authorization_context.set(context)
    try:
        yield context
    finally:
        _current_authorization_context.reset(token)
