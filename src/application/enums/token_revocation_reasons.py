"""Reasons for invalidating all outstanding authentication tokens."""

from enum import StrEnum


class TokenRevocationReason(StrEnum):
    """Business reasons for incrementing a user's token version."""

    USER_LOGOUT = "USER_LOGOUT"
    PASSWORD_CHANGE = "PASSWORD_CHANGE"
    PASSWORD_RESET = "PASSWORD_RESET"
