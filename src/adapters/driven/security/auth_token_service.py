"""
JWT Token Handler - JSON Web Token operations for authentication.

This module handles creation and validation of JWT tokens for user authentication.
Implements RFC 7519 standard claims for security and interoperability.
"""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Final, Literal, TypedDict, TypeGuard

from jose import JWTError, jwt

from src.adapters.driven.security.config import load_jwt_config

TokenType = Literal["access", "refresh"]


class TokenInput(TypedDict):
    """Required fields for creating a JWT token."""

    user_id: str | int
    username: str
    role: str
    token_version: int


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Decoded and validated JWT payload."""

    sub: str
    iat: int
    exp: int
    jti: str
    type: TokenType
    username: str
    role: str
    token_version: int

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TokenPayload | None:
        """Parse a raw JWT claims dict into a TokenPayload, or None if invalid."""
        sub = data.get("sub")
        iat = data.get("iat")
        exp = data.get("exp")
        jti = data.get("jti")
        token_type = data.get("type")
        username = data.get("username")
        role = data.get("role")
        token_version = data.get("token_version")

        if (
            not isinstance(sub, str)
            or not _is_int(iat)
            or not _is_int(exp)
            or not isinstance(jti, str)
            or token_type not in (_ACCESS, _REFRESH)
            or not isinstance(username, str)
            or not isinstance(role, str)
            or not _is_int(token_version)
        ):
            return None

        if not sub.strip() or not username.strip() or not role.strip():
            return None
        if iat < 0 or exp < 0 or token_version < 1:
            return None

        return cls(
            sub=sub,
            iat=iat,
            exp=exp,
            jti=jti,
            type=token_type,
            username=username,
            role=role,
            token_version=token_version,
        )


_ACCESS: Final[TokenType] = "access"
_REFRESH: Final[TokenType] = "refresh"


def _get_expiration_time(token_type: TokenType, base_time: datetime) -> datetime:
    """Calculate the expiration datetime for the given token type."""
    config = load_jwt_config()

    if token_type == _ACCESS:
        return base_time + timedelta(minutes=config.access_token_expire_minutes)

    return base_time + timedelta(days=config.refresh_token_expire_days)


def _build_payload(data: TokenInput, token_type: TokenType) -> TokenPayload:
    """Construct a TokenPayload with standard and custom claims."""
    now = datetime.now(UTC)
    expire = _get_expiration_time(token_type, now)

    return TokenPayload(
        sub=str(data["user_id"]),
        iat=int(now.timestamp()),
        exp=int(expire.timestamp()),
        jti=str(uuid.uuid4()),
        type=token_type,
        username=data["username"],
        role=data["role"],
        token_version=data["token_version"],
    )


def _is_int(value: object) -> TypeGuard[int]:
    """Return true only for real ints, excluding bools."""
    return isinstance(value, int) and not isinstance(value, bool)


def create_token(data: TokenInput, token_type: TokenType = _ACCESS) -> str:
    """
    Create a JWT token with standard RFC 7519 claims.

    Standard Claims Included:
    - sub (subject): User ID who the token is for
    - iat (issued at): When the token was created
    - exp (expiration): When the token expires
    - jti (JWT ID): Unique identifier for this token

    Custom Claims:
    - type: "access" or "refresh" to prevent token confusion
    - username: User's username
    - role: User's role (EMPLOYEE or MANAGER)
    - token_version: Integer for token revocation control

    Args:
        data: Dictionary containing user information.
              Must include: user_id, username, role, token_version.
        token_type: Type of token to create ("access" or "refresh")

    Returns:
        str: Encoded JWT token

    Raises:
        ValueError: If user_id is missing from data
        KeyError: If any required field is missing from data

    Example:
        >>> token_data = {"user_id": 123, "username": "johndoe", "role": "USER", "token_version": 1}
        >>> token = create_token(token_data)
        >>> print(token)
        'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...'

    """
    config = load_jwt_config()
    payload = _build_payload(data, token_type)

    return jwt.encode(
        asdict(payload),
        config.secret,
        algorithm=config.algorithm,
    )


def decode_token(
    token: str,
    expected_type: TokenType = _ACCESS,
) -> TokenPayload | None:
    """
    Decode and verify a JWT token.

    Validates:
    - Token signature (using SECRET_KEY)
    - Token expiration (exp claim)
    - Token type matches expected type

    Args:
        token: JWT token string to decode
        expected_type: Expected token type ("access" or "refresh")

    Returns:
        TokenPayload if valid, or None if the token is invalid, expired,
        malformed, or of the wrong type.

    Example:
        >>> payload = decode_token(access_token, expected_type="access")
        >>> if payload:
        ...     user_id = int(payload.sub)
        ...     print(f"Valid token for user {user_id}")
        ... else:
        ...     print("Invalid or expired token")

    """
    config = load_jwt_config()

    try:
        raw_payload = jwt.decode(
            token,
            config.secret,
            algorithms=[config.algorithm],
        )
    except JWTError:
        return None

    payload = TokenPayload.from_dict(raw_payload)
    if payload is None:
        return None

    if payload.type != expected_type:
        return None

    return payload


def get_user_id_from_token(token: str) -> int | None:
    """
    Extract user ID from a token (convenience function).

    Args:
        token: JWT token string

    Returns:
        int: User ID if token is valid
        None: If token is invalid
    """
    payload = decode_token(token)

    if not payload:
        return None

    try:
        return int(payload.sub) if payload.sub else None
    except (ValueError, TypeError):
        return None


def create_access_token(user_data: TokenInput) -> str:
    """
    Create an access token (short-lived).

    Convenience wrapper around create_token() for access tokens.

    Args:
        user_data: Dict with user_id, username, role, token_version

    Returns:
        str: Access token
    """
    return create_token(user_data, token_type="access")


def create_refresh_token(user_data: TokenInput) -> str:
    """
    Create a refresh token (long-lived).

    Refresh tokens are used to obtain new access tokens without re-authentication.
    They have much longer expiration (typically 7-30 days).

    Security Note:
    - Store refresh token hash in database for revocation
    - Implement token rotation on refresh
    - Add revocation mechanism

    Args:
        user_data: Dict with user_id, username, role, token_version

    Returns:
        str: Refresh token
    """
    return create_token(user_data, token_type="refresh")
