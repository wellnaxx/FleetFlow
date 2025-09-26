from dataclasses import dataclass
from typing import Any
import re

@dataclass
class ContactInfo:
    """Encapsulates a user's contact information."""
    name: str
    email: str = ""
    phone_number: str = "" 

    def normalized_phone(self) -> str:
        return self.phone_number

    def display_email(self) -> str:
        return self.email or "No email provided"

    def display_phone(self) -> str:
        return self.phone_number or "No phone number provided"

    def __post_init__(self):
        object.__setattr__(self, "name", self._clean_name(self.name))
        object.__setattr__(self, "email", self._clean_email(self.email))
        object.__setattr__(self, "phone_number", self._clean_phone(self.phone_number))

    def __setattr__(self, key: str, value: Any) -> None:
        if key == "name":
            value = self._clean_name(value)
        elif key == "email":
            value = self._clean_email(value)
        elif key == "phone_number":
            value = self._clean_phone(value)
        super().__setattr__(key, value)

    def _clean_name(self, v: Any) -> str:
        if not isinstance(v, str):
            raise ValueError("Name must be a string.")
        v = v.strip()
        if len(v) < 3:
            raise ValueError("Name is too short")
        if len(v) > 30:
            raise ValueError("Name is too long")
        return v

    def _clean_email(self, v) -> str:
        if v is None:
            return ""
        if not isinstance(v, str):
            raise ValueError("Email must be a string.")
        v = v.strip().lower()
        if v == "":
            return ""

        parts = v.split("@")
        if len(parts) != 2:
            raise ValueError("Invalid email address format.")
        local, domain = parts
        if not local or not domain:
            raise ValueError("Invalid email address format.")

        if ".." in v:
            raise ValueError("Invalid email address format.")

        labels = domain.split(".")
        if len(labels) < 2 or any(label == "" for label in labels):
            raise ValueError("Invalid email address format.")
        for label in labels:
            if not re.fullmatch(r"[a-z0-9-]+", label):
                raise ValueError("Invalid email address format.")
            if label.startswith("-") or label.endswith("-"):
                raise ValueError("Invalid email address format.")

        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+", local):
            raise ValueError("Invalid email address format.")

        return v

    def _clean_phone(self, v: Any) -> str:
        if not v:
            return ""
        if not isinstance(v, str):
            raise ValueError("Phone number must be a string")
        v = v.strip()
        if not v.isdigit():
            raise ValueError("Phone number must contain only digits")
        if len(v) != 10:
            raise ValueError("Invalid phone number. Phone number must be exactly 10 digits.")
        if not v.startswith("04"):
            raise ValueError("Australian mobile numbers start with '04'.")
        return v