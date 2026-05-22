from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status

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
from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.composition.runtime import get_auth_service, get_user_repository
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
    """Generate a TokenResponse containing new access and refresh tokens for the given user record.

    Args:
        record: The user record for which to generate tokens.

    Returns:
        A TokenResponse containing the generated access token and refresh token.
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
    """Convert a UserRecord into a CurrentUserResponse for API responses.

    Args:
        record: The user record to convert.

    Returns:
        A CurrentUserResponse containing the user's details.
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
        request: The registration details extracted from the request body.
        use_case: The RegisterUserUseCase instance for executing the registration logic.

    Returns:
        A CurrentUserResponse containing details about the newly registered user.

    Raises:
        HTTPException: If registration fails due to invalid input,
        authentication issues, or authorization issues.
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
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
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
        form_data: The login credentials extracted from the form data.
        auth_service: The authentication service for handling the login logic.

    Returns:
        A TokenResponse containing the access token and refresh token.

    Raises:
        HTTPException: If authentication fails due to invalid credentials or user record issues.
    """
    try:
        record, _ = auth_service.authenticate(form_data.username, form_data.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
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
        request: The current and new passwords extracted from the request.
        principal: The currently authenticated user, provided by the `get_current_user` dependency.
        use_case: The ChangePasswordUseCase instance for executing the password change.

    Returns:
        None

    Raises:
        HTTPException: If the password change fails due to invalid input,
        authentication issues, or authorization issue
    """
    try:
        use_case.execute_current_user(
            username=principal.record.username,
            new_password=request.new_password,
            old_password=request.current_password,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@auth_router.post("/users/{username}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    username: str,
    request: ResetUserPasswordRequest,
    use_case: Annotated[ChangePasswordUseCase, Depends(get_change_password_use_case)],
) -> None:
    """Reset another user's password. This endpoint is intended for admin use.
    
    Args:
        username: The username of the user whose password is to be reset.
        request: The new password extracted from the request.
        use_case: The ChangePasswordUseCase instance for executing the password reset.

    Returns:
        None

    Raises:
        HTTPException: If the password reset fails due to invalid input,
        authentication issues, or authorization issues.
    """
    try:
        use_case.execute(username=username, new_password=request.new_password)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@auth_router.post("/refresh", status_code=status.HTTP_200_OK)
def refresh_token(
    data: RefreshRequest, user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)]
) -> TokenResponse:
    """Exchange a valid refresh token for a new access token.

    Args:
        data: The refresh token request payload, containing the refresh token to exchange.
        user_repository: Repository for querying user records to validate the token and generate new tokens.

    Returns:
        A TokenResponse containing the new access token and refresh token.

    Raises:
        HTTPException: If the refresh token is invalid or expired.
    """
    principal = principal_from_token(data.refresh_token, user_repository, expected_type="refresh")
    return _token_response(principal.record)


@auth_router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
    user_repository: Annotated[UserRepositoryPort, Depends(get_user_repository)],
) -> None:
    """Invalidate all sessions for the current user.

    Implementation: increments `users.token_version`, which invalidates all existing
    access and refresh tokens for that user immediately.

    Args:
        principal: The currently authenticated user, provided by the `get_current_user` dependency.
        user_repository: Repository for querying and updating user records.

    Missing users are treated as already logged out because the endpoint is
    idempotent. Repository write failures should surface as repository
    exceptions.
    """
    user_repository.increment_token_version_by_id(principal.record.user_id)


@auth_router.get("/me", status_code=status.HTTP_200_OK)
def me(
    principal: Annotated[AuthenticatedPrincipal, Depends(get_current_user)],
) -> CurrentUserResponse:
    """Get details about the currently authenticated user.

    Args:
        principal: The currently authenticated user, provided by the `get_current_user` dependency.

    Returns:
        A CurrentUserResponse containing details about the authenticated user.

    Raises:
        HTTPException: If the user details cannot be retrieved.
    """
    return _current_user_response(principal.record)
