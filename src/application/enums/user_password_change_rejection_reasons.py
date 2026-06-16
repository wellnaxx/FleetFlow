from enum import StrEnum


class UserPasswordChangeRejectionReason(StrEnum):
    """Business reasons for rejecting a user's password change attempt."""

    CURRENT_PASSWORD_INCORRECT = "CURRENT_PASSWORD_INCORRECT"
    PASSWORD_CRITERIA_NOT_MET = "PASSWORD_CRITERIA_NOT_MET"
    SAME_AS_CURRENT_PASSWORD = "SAME_AS_CURRENT_PASSWORD"
