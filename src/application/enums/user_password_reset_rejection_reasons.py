from enum import StrEnum


class UserPasswordResetRejectionReason(StrEnum):
    """Business reasons for when an administrator's attempt to reset a user's password is rejected."""

    INVALID_USERNAME = "INVALID_USERNAME"
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PASSWORD_CRITERIA_NOT_MET = "PASSWORD_CRITERIA_NOT_MET"
    CANNOT_RESET_OWN_PASSWORD = "CANNOT_RESET_OWN_PASSWORD"