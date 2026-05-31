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
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ValidationError,
)
from src.application.models.user_record import UserRecord
from src.application.services.auth_service import AuthService
from src.application.use_cases.auth.change_password import ChangePasswordUseCase
from src.application.use_cases.auth.register_user import RegisterUserUseCase
from src.composition.runtime import get_auth_service, get_user_repository
from src.domain.enums.auth import Role
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

    Raises:
        ValidationError: If the persisted role cannot be serialized safely.
    """
    try:
        role = Role(record.role)
    except ValueError as exc:
        raise ValidationError("Invalid persisted user role.") from exc

    token_input: TokenInput = {
        "user_id": record.user_id,
        "username": record.username,
        "role": role.value,
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
        email=record.email or None,
        phone_number=record.phone_number or None,
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
        HTTPException: Raised with:
            * 400 - Invalid registration input.
            * 403 - Insufficient permissions.
            * 409 - Username already exists.
            * 500 - Database operation failure.
    """
    record = use_case.execute(
        username=request.username,
        role=request.role,
        name=request.name,
        email=request.email or "",
        phone_number=request.phone_number or "",
        password=request.password,
    )

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
        HTTPException: Raised with:
            * 400 - Invalid persisted user auth data.
            * 401 - Invalid username or password.
            * 500 - Database operation failure.
    """
    try:
        record, _ = auth_service.authenticate(form_data.username, form_data.password)
        return _token_response(record)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc


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
        HTTPException: Raised with:
            * 400 - Incorrect current password or invalid new password.
            * 403 - Insufficient permissions.
            * 404 - Current user record no longer exists.
            * 500 - Database operation failure.
    """
    try:
        use_case.execute_current_user(
            username=principal.record.username,
            new_password=request.new_password,
            old_password=request.current_password,
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


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
        HTTPException: Raised with:
            * 400 - Invalid new password.
            * 403 - Insufficient permissions.
            * 404 - Target user does not exist.
            * 500 - Database operation failure.
    """
    use_case.execute(username=username, new_password=request.new_password)


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
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, or userless refresh token.
    """
    try:
        principal = principal_from_token(data.refresh_token, user_repository, expected_type="refresh")
        return _token_response(principal.record)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        ) from exc


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
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, or userless access token.
            * 500 - Database operation failure.
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
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, or userless access token.
    """
    return _current_user_response(principal.record)
