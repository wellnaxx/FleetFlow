from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, status

from src.adapters.driven.security.auth_token_service import (
    TokenInput,
    create_access_token,
    create_refresh_token,
)
from src.adapters.driving.http.dependencies.auth import (
    AuthenticatedHTTPPrincipal,
    get_current_user,
    principal_from_token,
)
from src.adapters.driving.http.dependencies.message_buses import (
    get_authenticated_command_bus,
    get_command_bus,
)
from src.adapters.driving.http.schemas.auth import (
    ChangeOwnPasswordRequest,
    CurrentUserResponse,
    RefreshRequest,
    RegisterUserRequest,
    ResetUserPasswordRequest,
    TokenResponse,
)
from src.application.commands.auth.change_password import CHANGE_OWN_PASSWORD, ChangeOwnPasswordCommand
from src.application.commands.auth.login import LOGIN, LoginCommand
from src.application.commands.auth.logout import LOGOUT, LogoutCommand
from src.application.commands.auth.register_user import REGISTER_USER, RegisterUserCommand
from src.application.commands.auth.reset_password import RESET_USER_PASSWORD, ResetUserPasswordCommand
from src.application.exceptions.application_errors import (
    AuthenticationError,
    ValidationError,
)
from src.application.models.user_record import UserRecord
from src.composition.runtime import get_user_repository
from src.domain.enums.auth import Role
from src.ports.input.command_bus import CommandBus
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


@auth_router.post("/register", status_code=status.HTTP_201_CREATED)
def register(
    request: RegisterUserRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> CurrentUserResponse:
    """Register a new user account.

    Args:
        request: Registration request body.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns registration-event publication.

    Returns:
        A response model representing the newly registered user.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid registration input.
            * 403 - Insufficient permissions.
            * 409 - Username already exists.
            * 500 - Database operation failure.
    """

    record = command_bus.dispatch(
        key=REGISTER_USER,
        command=RegisterUserCommand(
            username=request.username,
            role=request.role,
            name=request.name,
            email=request.email or "",
            phone_number=request.phone_number or "",
            password=request.password,
        ),
    )

    return CurrentUserResponse.from_record(record)


@auth_router.post("/login", status_code=status.HTTP_200_OK)
def login(
    form_data: Annotated[LoginFormData, Depends(_get_login_form_data)],
    command_bus: Annotated[CommandBus, Depends(get_command_bus)],
) -> TokenResponse:
    """Authenticate with username/password and return an access + refresh token pair.

    Args:
        form_data: Login credentials extracted from form data.
        command_bus: Public command bus injected by FastAPI. The registered
            executor owns authentication-event publication.

    Returns:
        A token response containing a new access token and refresh token.

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid persisted user auth data.
            * 401 - Invalid username or password.
            * 500 - Database operation failure.
    """
    try:
        result = command_bus.dispatch(
            key=LOGIN,
            command=LoginCommand(
                username=form_data.username,
                password=form_data.password,
            ),
        )
        return _token_response(result.record)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password.",
        ) from exc


@auth_router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    request: ChangeOwnPasswordRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> None:
    """Change the current user's password.

    Args:
        request: Current and new password request body.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns password-change event publication.

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
        command_bus.dispatch(
            key=CHANGE_OWN_PASSWORD,
            command=ChangeOwnPasswordCommand(
                current_password=request.current_password, new_password=request.new_password
            ),
        )
    except AuthenticationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@auth_router.post("/users/{username}/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    username: str,
    request: ResetUserPasswordRequest,
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> None:
    """Reset another user's password. This endpoint is intended for admin use.

    Args:
        username: Username of the user whose password should be reset.
        request: New password request body.
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns password-reset event publication.

    Returns:
        None

    Raises:
        HTTPException: Raised with:
            * 400 - Invalid new password.
            * 403 - Insufficient permissions.
            * 404 - Target user does not exist.
            * 500 - Database operation failure.
    """
    command_bus.dispatch(
        key=RESET_USER_PASSWORD,
        command=ResetUserPasswordCommand(
            username=username,
            new_password=request.new_password,
        ),
    )


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
    command_bus: Annotated[CommandBus, Depends(get_authenticated_command_bus)],
) -> None:
    """Invalidate all sessions for the current user.

    Args:
        command_bus: Authenticated command bus injected by FastAPI. The
            registered executor owns token-revocation and session-end event
            publication.

    Returns:
        None

    Raises:
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, or userless access token.
            * 500 - Database operation failure.
    """
    command_bus.dispatch(key=LOGOUT, command=LogoutCommand())


@auth_router.get("/me", status_code=status.HTTP_200_OK)
def me(
    principal: Annotated[AuthenticatedHTTPPrincipal, Depends(get_current_user)],
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
    return CurrentUserResponse.from_record(principal.record)
