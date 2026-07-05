from collections.abc import AsyncGenerator
from dataclasses import dataclass, replace

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.adapters.driven.security.auth_token_service import TokenPayload, TokenType, decode_token
from src.application.eventing.current_context import bind_event_context, get_event_context
from src.application.eventing.envelope import EventActor
from src.application.exceptions.application_errors import UnsupportedRoleError, ValidationError
from src.application.models.current_user_principal import CurrentUserPrincipal
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.application.services.runtime_user_factory import create_runtime_authenticated_user_from_record
from src.composition.runtime import get_user_repository
from src.ports.output.user_repository import UserRepositoryPort

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedHTTPPrincipal:
    """HTTP-authenticated request identity and validated token metadata."""

    record: UserRecord
    current_user: CurrentUserPrincipal
    authz: AuthorizationService
    token: TokenPayload


def _runtime_user_from_record(record: UserRecord) -> CurrentUserPrincipal:
    """Convert a persisted user record into a current-user principal.

    Args:
        record: The UserRecord retrieved from the user repository.

    Returns:
        Current-user principal corresponding to the persisted user's role.

    Raises:
        HTTPException: Raised with:
            * 401 - Invalid or unsupported user role.
    """
    try:
        return create_runtime_authenticated_user_from_record(record)
    except ValidationError as exc:
        detail = "Unsupported user role" if isinstance(exc, UnsupportedRoleError) else "Invalid user role"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        ) from exc


def principal_from_token(
    token: str,
    user_repo: UserRepositoryPort,
    *,
    expected_type: TokenType = "access",
) -> AuthenticatedHTTPPrincipal:
    """Validate a JWT token and construct an authenticated HTTP principal.

    Args:
        token: The JWT token to validate.
        user_repo: The user repository to retrieve user information.
        expected_type: The expected type of the token ("access" or "refresh").

    Returns:
        HTTP principal containing the persisted record, current-user principal,
        request-scoped authorization service, and decoded token.

    Raises:
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, mismatched, or userless token.
    """
    payload = decode_token(token, expected_type=expected_type)
    if payload is None:
        detail = (
            "Invalid or expired refresh token." if expected_type == "refresh" else "Invalid or expired token."
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

    try:
        user_id = int(payload.sub)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.") from exc

    record = user_repo.get_by_id(user_id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")

    if record.username != payload.username:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token user mismatch.")

    if record.token_version != payload.token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked.")

    user = _runtime_user_from_record(record)
    authz = AuthorizationService(current_user=user)
    return AuthenticatedHTTPPrincipal(record=record, current_user=user, authz=authz, token=payload)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> AsyncGenerator[AuthenticatedHTTPPrincipal]:
    """Dependency to retrieve the currently authenticated user based on the provided JWT token.

    Args:
        token: The JWT token provided in the Authorization header.
        user_repo: The user repository to retrieve user information.

    Yields:
        Authenticated HTTP principal representing the current request user
        while an actor-enriched event context is bound.

    Raises:
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, mismatched, or userless token.
    """
    principal = principal_from_token(token, user_repo)

    request_context = get_event_context()
    actor_context = replace(
        request_context,
        actor=EventActor(
            user_id=principal.current_user.user_id,
            username=principal.current_user.username,
        ),
    )

    with bind_event_context(actor_context):
        yield principal


def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> AuthenticatedHTTPPrincipal | None:
    """Dependency to optionally retrieve the currently authenticated user based on the provided JWT token.

    Args:
        token: The JWT token provided in the Authorization header, or None if not provided.
        user_repo: The user repository to retrieve user information.

    Returns:
        Authenticated HTTP principal representing the current request user,
            or None if no valid token is provided

    Raises:
        HTTPException: Raised with:
            * 401 - Invalid, expired, revoked, mismatched, or userless token.
    """
    if not token:
        return None

    return principal_from_token(token, user_repo)
