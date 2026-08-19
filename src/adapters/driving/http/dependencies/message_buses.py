"""FastAPI dependencies exposing public and authenticated message buses."""

from typing import Annotated

from fastapi import Depends

from src.adapters.driving.http.dependencies.auth import AuthenticatedHTTPPrincipal, get_current_user
from src.composition.container import Container
from src.composition.runtime import get_container
from src.ports.input.command_bus import CommandBus
from src.ports.input.query_bus import QueryBus


def get_command_bus(
    container: Annotated[Container, Depends(get_container)],
) -> CommandBus:
    """Return the command bus for a public HTTP workflow.

    Public workflows such as login still execute inside the request event
    context established by HTTP middleware, but they must not require an
    already authenticated principal.

    Args:
        container: Application container owning the configured command bus.

    Returns:
        Dispatch-only command-bus input port.
    """
    return container.command_bus


def get_authenticated_command_bus(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> CommandBus:
    """Return the command bus after authenticating and binding the request.

    FastAPI resolves ``get_current_user`` before this dependency, which binds
    the request's authorization and event contexts for downstream handlers.

    Args:
        principal: Authenticated request principal. Its value is not passed to
            the bus because handlers read the request-scoped authorization
            context.
        container: Application container owning the configured command bus.

    Returns:
        Dispatch-only command-bus input port.
    """
    del principal
    return container.command_bus


def get_authenticated_query_bus(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
    container: Annotated[Container, Depends(get_container)],
) -> QueryBus:
    """Return the query bus after authenticating and binding the request.

    FastAPI resolves ``get_current_user`` before this dependency, which binds
    the request's authorization and event contexts for downstream handlers.

    Args:
        principal: Authenticated request principal. Its value is not passed to
            the bus because handlers read the request-scoped authorization
            context.
        container: Application container owning the configured query bus.

    Returns:
        Dispatch-only query-bus input port.
    """
    del principal
    return container.query_bus
