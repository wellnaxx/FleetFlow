"""Persistence model for auth users."""

from dataclasses import dataclass


@dataclass
class UserRecord:
    """Serializable auth user record used by persistence adapters."""

    user_id: int
    username: str
    role: str
    name: str
    email: str
    phone_number: str
    password: str
