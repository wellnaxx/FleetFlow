"""Password hashing and persisted hash validation."""

import base64
import binascii
import hashlib
import hmac
import os
from dataclasses import dataclass

PBKDF2_ALGO = "sha256"
PBKDF2_ITERATIONS = 200_000
SALT_BYTES = 16


@dataclass(frozen=True)
class PasswordHash:
    """Serialized PBKDF2 password hash components."""

    algo: str
    iterations: int
    salt_b64: str
    hash_b64: str

    def serialize(self) -> str:
        """Return the persisted password hash string.

        Returns:
            Hash string in the application storage format.
        """
        # e.g. pbkdf2_sha256$200000$<salt>$<hash>
        return f"pbkdf2_{self.algo}${self.iterations}${self.salt_b64}${self.hash_b64}"

    @staticmethod
    def parse(value: object) -> "PasswordHash":
        """Parse and validate a persisted password hash.

        Args:
            value: Persisted hash value to parse.

        Returns:
            Parsed password hash object.

        Raises:
            TypeError: If the value is not a string.
            ValueError: If the hash does not match the application policy.
        """
        if not isinstance(value, str):
            raise TypeError("Invalid password hash.")

        parts = value.split("$")
        if len(parts) != 4:
            raise ValueError("Invalid password hash.")

        scheme, iterations_text, salt_b64, hash_b64 = parts

        expected_scheme = f"pbkdf2_{PBKDF2_ALGO}"
        if scheme != expected_scheme:
            raise ValueError("Invalid password hash.")

        algo = PBKDF2_ALGO

        try:
            iterations = int(iterations_text)
        except ValueError as exc:
            raise ValueError("Invalid password hash.") from exc

        if iterations < PBKDF2_ITERATIONS:
            raise ValueError("Invalid password hash.")

        try:
            salt = base64.b64decode(salt_b64, validate=True)
            hash_value = base64.b64decode(hash_b64, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid password hash.") from exc
        if len(salt) != SALT_BYTES or not hash_value:
            raise ValueError("Invalid password hash.")

        return PasswordHash(
            algo=algo,
            iterations=iterations,
            salt_b64=salt_b64,
            hash_b64=hash_b64,
        )


def hash_password(plain: str) -> PasswordHash:
    """Hash a plaintext password using the application PBKDF2 policy.

    Args:
        plain: Plaintext password.

    Returns:
        Password hash ready for persistence.

    Raises:
        ValueError: If the password is too short.
    """
    if len(plain) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALGO, plain.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return PasswordHash(
        algo=PBKDF2_ALGO,
        iterations=PBKDF2_ITERATIONS,
        salt_b64=base64.b64encode(salt).decode("ascii"),
        hash_b64=base64.b64encode(dk).decode("ascii"),
    )


def verify_password(plain: str, stored: PasswordHash) -> bool:
    """Verify a plaintext password against a stored password hash.

    Args:
        plain: Plaintext password to verify.
        stored: Parsed persisted hash.

    Returns:
        True when the password matches the stored hash.
    """
    salt = base64.b64decode(stored.salt_b64)
    dk2 = hashlib.pbkdf2_hmac(stored.algo, plain.encode("utf-8"), salt, stored.iterations)
    return hmac.compare_digest(base64.b64encode(dk2).decode("ascii"), stored.hash_b64)
