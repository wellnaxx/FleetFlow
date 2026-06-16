from enum import StrEnum


class UserRegistrationRejectionReason(StrEnum):
    """Business reasons for rejecting a user's registration."""

    INVALID_USERNAME = "INVALID_USERNAME"
    PASSWORD_CRITERIA_NOT_MET = "PASSWORD_CRITERIA_NOT_MET"
    USERNAME_ALREADY_EXISTS = "USERNAME_ALREADY_EXISTS"
