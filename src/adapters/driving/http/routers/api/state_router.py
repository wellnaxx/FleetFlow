from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driving.http.dependencies.use_cases import (
    get_load_world_state_use_case,
    get_save_world_state_use_case,
)
from src.adapters.driving.http.schemas.state import WorldStatePathRequest, WorldStatePathResponse
from src.application.exceptions.application_errors import ValidationError
from src.application.exceptions.world_state_errors import (
    WorldStateCorruptionError,
    WorldStateFileNotFoundError,
    WorldStatePersistenceError,
    WorldStateRuntimeSwapError,
)
from src.application.use_cases.state.load_world import LoadWorldStateUseCase
from src.application.use_cases.state.save_world import SaveWorldStateUseCase

state_router = APIRouter(prefix="/state", tags=["state"])


@state_router.post("/save", status_code=status.HTTP_200_OK)
def save_world(
    use_case: Annotated[SaveWorldStateUseCase, Depends(get_save_world_state_use_case)],
    request: WorldStatePathRequest,
) -> WorldStatePathResponse:
    """Save the current world state to a snapshot path.

    Args:
        use_case: Use case for saving world state, injected by FastAPI.
        request: Snapshot path request.

    Returns:
        Resolved path metadata for the saved snapshot.

    Raises:
        HTTPException 400: If the requested snapshot path is invalid.
        HTTPException 403: If the caller lacks permission to save world state.
        HTTPException 500: If snapshot export or persistence fails.
    """
    try:
        path = use_case.execute(request.path)
        return WorldStatePathResponse(path=path, message="World state saved.")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (DatabaseError, WorldStatePersistenceError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="World state persistence failed.",
        ) from exc


@state_router.post("/load", status_code=status.HTTP_200_OK)
def load_world(
    use_case: Annotated[LoadWorldStateUseCase, Depends(get_load_world_state_use_case)],
    request: WorldStatePathRequest,
) -> WorldStatePathResponse:
    """Load world state from a snapshot path.

    Args:
        use_case: Use case for loading world state, injected by FastAPI.
        request: Snapshot path request.

    Returns:
        Resolved path metadata for the loaded snapshot.

    Raises:
        HTTPException 400: If the requested snapshot path is invalid or the snapshot is malformed.
        HTTPException 403: If the caller lacks permission to load world state.
        HTTPException 404: If the requested snapshot does not exist.
        HTTPException 500: If snapshot import or persistence fails.
    """
    try:
        path = use_case.execute(request.path)
        return WorldStatePathResponse(path=path, message="World state loaded.")
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except WorldStateFileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="World state snapshot not found.",
        ) from exc
    except WorldStateCorruptionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="World state snapshot is malformed.",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except (DatabaseError, WorldStatePersistenceError, WorldStateRuntimeSwapError) as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="World state persistence failed.",
        ) from exc
