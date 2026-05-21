from pydantic import BaseModel, EmailStr, Field, field_validator

from src.domain.enums.auth import Role


class LoginRequest(BaseModel):
    """Request body for user login."""

    username: str = Field(min_length=1, description="Username of the user.")
    password: str = Field(
        min_length=8,
        max_length=128,
        repr=False,
        description="Password of the user.",
    )


class RegisterUserRequest(BaseModel):
    """Request body for user registration."""

    username: str = Field(min_length=1, description="Desired username for the new user.")
    role: Role = Field(..., description="Role for the new user (e.g., manager, employee).")
    name: str = Field(..., description="Full name of the new user.")
    email: EmailStr | None = Field(default=None, description="Email address of the new user.")
    phone_number: str | None = Field(default=None, description="Phone number of the new user.")
    password: str = Field(
        min_length=8,
        max_length=128,
        repr=False,
        description="Password for the new user.",
    )

    @field_validator("role", mode="before")
    @classmethod
    def normalize_role(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class TokenResponse(BaseModel):
    """Response body for successful authentication, containing JWT tokens."""

    access_token: str = Field(
        ...,
        repr=False,
        description="Short-lived JWT access token (type=access).",
    )
    refresh_token: str = Field(
        ...,
        repr=False,
        description="Long-lived JWT refresh token (type=refresh).",
    )
    token_type: str = Field("bearer", description="Token type for Authorization header.")


class RefreshRequest(BaseModel):
    """Payload for the token-refresh endpoint."""

    refresh_token: str = Field(
        ...,
        repr=False,
        description="Valid refresh token to exchange for new access token.",
    )


class ChangeOwnPasswordRequest(BaseModel):
    """Request body for changing the current user's password."""

    current_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        repr=False,
        description="Current password of the user.",
    )
    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        repr=False,
        description="New password for the user.",
    )


class ResetUserPasswordRequest(BaseModel):
    """Request body for resetting another user's password (manager-only)."""

    new_password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        repr=False,
        description="New password for the target user.",
    )


class CurrentUserResponse(BaseModel):
    """Response body for the current user endpoint."""

    user_id: int = Field(..., description="Unique identifier of the authenticated user.")
    username: str = Field(..., description="Username of the authenticated user.")
    role: str = Field(..., description="Role of the authenticated user (e.g., manager, employee).")
    name: str = Field(..., description="Full name of the authenticated user.")
    email: str | None = Field(default=None, description="Email address of the authenticated user.")
    phone_number: str | None = Field(default=None, description="Phone number of the authenticated user.")
