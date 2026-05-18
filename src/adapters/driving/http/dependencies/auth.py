from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.adapters.driven.security.auth_token_service import TokenPayload, decode_token
from src.application.models.user_record import UserRecord
from src.application.services.authorization_service import AuthorizationService
from src.composition.runtime import get_user_repository
from src.domain.entities.users.employee import Employee
from src.domain.entities.users.manager import Manager
from src.domain.entities.users.user import User
from src.domain.enums.auth import Role
from src.ports.output.user_repository import UserRepositoryPort

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


@dataclass(frozen=True, slots=True)
class AuthenticatedPrincipal:
    record: UserRecord
    user: User
    authz: AuthorizationService
    token: TokenPayload


def _runtime_user_from_record(record: UserRecord) -> User:
    try:
        role = Role(record.role)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user role",
        ) from exc

    if role is Role.MANAGER:
        return Manager(record.user_id, record.name, record.email, record.phone_number)
    if role is Role.EMPLOYEE:
        return Employee(record.user_id, record.name, record.email, record.phone_number)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Unsupported user role",
    )


def _principal_from_token(token: str, user_repo: UserRepositoryPort) -> AuthenticatedPrincipal:
    payload = decode_token(token, expected_type="access")
    if payload is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token.")

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
    return AuthenticatedPrincipal(record=record, user=user, authz=authz, token=payload)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> AuthenticatedPrincipal:
    return _principal_from_token(token, user_repo)


def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    user_repo: UserRepositoryPort = Depends(get_user_repository),
) -> AuthenticatedPrincipal | None:
    if not token:
        return None
    try:
        return _principal_from_token(token, user_repo)
    except HTTPException:
        return None
