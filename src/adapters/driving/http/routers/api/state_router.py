from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.message_buses import get_authenticated_command_bus
from src.adapters.driving.http.schemas.state import WorldStatePathRequest, WorldStatePathResponse
from src.application.commands.state.load_world import LOAD_WORLD, LoadWorldCommand
from src.application.commands.state.save_world import SAVE_WORLD, SaveWorldCommand
from src.application.exceptions.world_state_errors import (
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.ports.input.command_bus import CommandBus

state_router = APIRouter(prefix="/state", tags=["state"])


@state_router.post("/save", status_code=status.HTTP_200_OK)
def save_world(
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
    request: WorldStatePathRequest,
) -> WorldStatePathResponse:
    """Save the current world state to a snapshot path.

    Args:
        command_bus: Authenticated command bus whose registered executor owns
            authorization and export-event publication.
        request: Snapshot path request.

    Returns:
        Resolved path metadata for the saved snapshot.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid snapshot path.
            * 403 - Insufficient permissions.
            * 500 - Snapshot export or persistence failure.
    """
    try:
        path = command_bus.dispatch(
            key=SAVE_WORLD,
            command=SaveWorldCommand(path=request.path),
        )
        return WorldStatePathResponse(path=path, message="World state saved.")
    except (DatabaseError, WorldStatePersistenceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="World state persistence failed.",
        ) from exc


@state_router.post("/load", status_code=status.HTTP_200_OK)
def load_world(
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
    request: WorldStatePathRequest,
) -> WorldStatePathResponse:
    """Load world state from a snapshot path.

    Args:
        command_bus: Authenticated command bus whose registered executor owns
            authorization and import-event publication.
        request: Snapshot path request.

    Returns:
        Resolved path metadata for the loaded snapshot.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid snapshot path or malformed snapshot.
            * 403 - Insufficient permissions.
            * 404 - Snapshot not found.
            * 500 - Snapshot import or persistence failure.
    """
    try:
        path = command_bus.dispatch(
            key=LOAD_WORLD,
            command=LoadWorldCommand(path=request.path),
        )
        return WorldStatePathResponse(path=path, message="World state loaded.")
    except WorldStateFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World state snapshot not found.",
        ) from exc
    except (DatabaseError, WorldStatePersistenceError, WorldStateRuntimeSwapError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="World state persistence failed.",
        ) from exc
