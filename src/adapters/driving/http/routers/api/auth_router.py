from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.adapters.driven.persistence.database.errors import DatabaseError
from src.adapters.driven.security.auth_token_service import (
    TokenInput,
    create_access_token,
    create_refresh_token,
)
from src.adapters.driving.http.dependencies.auth import (
    AuthenticatedPrincipal,
    get_current_user,
    principal_from_token,
)
from src.adapters.driving.http.dependencies.use_cases import (
    get_change_password_use_case,
    get_register_user_use_case,
)
from src.adapters.driving.http.schemas.auth import (
    ChangeOwnPasswordRequest,
    CurrentUserResponse,
    RefreshRequest,
    RegisterUserRequest,
    ResetUserPasswordRequest,
    TokenResponse,
)
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ConflictError,
    NotFoundError,
    ValidationError,
)
from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.composition.runtime import get_auth_service, get_user_repository
from src.domain.exceptions import DomainValidationError
from src.ports.output.user_repository import UserRepositoryPort

auth_router = APIRouter(prefix="/auth", tags=["auth"])


@dataclass(frozen=True, slots=True)
class LoginFormData:
    """Container for OAuth2-style form login credentials.

    Attributes:
        username: The username field from the form data.
        password: The password field from the form data.
    """

    username: str
    password: str


def _get_login_form_data(
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
) -> LoginFormData:
    """FastAPI dependency that extracts login credentials from form data.

    Args:
        username: The username field from the form data.
        password: The password field from the form data.

    Returns:
        A LoginFormData instance containing the extracted credentials.

    FastAPI validates the required `Form()` fields and returns 422 when
    username or password is missing.
    """
    return LoginFormData(username=username, password=password)


def _token_response(record: UserRecord) -> TokenResponse:
    """Build an auth token response for a persisted user.

    Args:
        record: User record used to populate token claims.

    Returns:
        A token response containing a new access token and refresh token.
    """
    token_input: TokenInput = {
        "user_id": record.user_id,
        "username": record.username,
        "role": record.role,
        "token_version": record.token_version,
    }
    return TokenResponse(
        access_token=create_access_token(token_input),
        refresh_token=create_refresh_token(token_input),
        token_type="bearer",
    )


def _current_user_response(record: UserRecord) -> CurrentUserResponse:
    """Convert a persisted user record to a current-user response model.

    Args:
        record: User record to convert.

    Returns:
        A response model representing the user.
    """
    return CurrentUserResponse(
        user_id=record.user_id,
        username=record.username,
        role=record.role,
        name=record.name,
        email=record.email,
        phone_number=record.phone_number,
    )


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterUserRequest,
    use_case: Annotated[RegisterUserUseCase, Depends(get_register_user_use_case)],
) -> CurrentUserResponse:
    """Register a new user account.

    Args:
        request: Registration request body.
        use_case: Use case for registering users, injected by FastAPI.

    Returns:
        A response model representing the newly registered user.

    Raises:
        HTTPException 400: If the registration request contains invalid input.
        HTTPException 403: If the caller lacks permission to register users.
        HTTPException 409: If the username already exists.
        HTTPException 500: If the database fails to create the user.
    """
    try:
        record = use_case.execute(
            username=request.username,
            role=request.role,
            name=request.name,
            email=request.email or "",
            phone_number=request.phone_number or "",
            password=request.password,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except (ValidationError, DomainValidationError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except ConflictError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc
    except TypeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return _current_user_response(record)


@auth_router.post("/login", status_code=status.HTTP_200_OK)
def login(
    form_data: Annotated[LoginFormData, Depends(_get_login_form_data)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    """Authenticate with username/password and return an access + refresh token pair.

    Args:
        form_data: Login credentials extracted from form data.
        auth_service: Authentication service, injected by FastAPI.

    Returns:
        A token response containing a new access token and refresh token.

    Raises:
        HTTPException 400: If persisted user auth data is invalid.
        HTTPException 401: If the username or password is invalid.
        HTTPException 500: If the database fails during authentication.
    """
    try:
        record, _ = auth_service.authenticate(form_data.username, form_data.password)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc

    return _token_response(record)


@auth_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: ChangeOwnPasswordRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    use_case: Annotated[ChangePasswordUseCase, Depends(get_change_password_use_case)],
) -> None:
    """Change the current user's password.

    Args:
        request: Current and new password request body.
        principal: Currently authenticated user, injected by FastAPI.
        use_case: Use case for changing passwords, injected by FastAPI.

    Returns:
        None

    Raises:
        HTTPException 400: If the current password is wrong or the new password is invalid.
        HTTPException 403: If the caller lacks permission to change their password.
        HTTPException 404: If the current user record no longer exists.
        HTTPException 500: If the database fails to update the password.
    """
    try:
        use_case.execute_current_user(
            username=principal.record.username,
            new_password=request.new_password,
            old_password=request.current_password,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc


@auth_router.post("/users/{username}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    username: str,
    request: ResetUserPasswordRequest,
    use_case: Annotated[ChangePasswordUseCase, Depends(get_change_password_use_case)],
) -> None:
    """Reset another user's password. This endpoint is intended for admin use.

    Args:
        username: Username of the user whose password should be reset.
        request: New password request body.
        use_case: Use case for changing passwords, injected by FastAPI.

    Returns:
        None

    Raises:
        HTTPException 400: If the new password is invalid.
        HTTPException 403: If the caller lacks permission to reset passwords.
        HTTPException 404: If the target user does not exist.
        HTTPException 500: If the database fails to update the password.
    """
    try:
        use_case.execute(username=username, new_password=request.new_password)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except NotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except DatabaseError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database operation failed."
        ) from exc


@auth_router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_token(
    data: RefreshRequest, user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)]
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token.

    Args:
        data: Refresh token request body.
        user_repository: Repository used to validate the token's user record, injected by FastAPI.

    Returns:
        A token response containing a new access token and refresh token.

    Raises:
        HTTPException 401: If the refresh token is invalid, expired, revoked, or references an invalid user.
    """
    principal = principal_from_token(data.refresh_token, user_repository, expected_type="refresh")
    return _token_response(principal.record)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)],
) -> None:
    """Invalidate all sessions for the current user.

    Args:
        principal: Currently authenticated user, injected by FastAPI.
        user_repository: Repository used to increment token version, injected by FastAPI.

    Returns:
        None

    Raises:
        HTTPException 401: If the access token is invalid, expired, revoked, or references an invalid user.
    """
    user_repository.increment_token_version_by_id(principal.record.user_id)


@auth_router.get("/me", status_code=status.HTTP_200_OK)
def me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Get details about the currently authenticated user.

    Args:
        principal: Currently authenticated user, injected by FastAPI.

    Returns:
        A response model representing the authenticated user.

    Raises:
        HTTPException 401: If the access token is invalid, expired, revoked, or references an invalid user.
    """
    return _current_user_response(principal.record)
