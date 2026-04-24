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
    algo: str
    iterations: int
    salt_b64: str
    hash_b64: str

    def serialize(self) -> str:
        # e.g. pbkdf2_sha256$200000$<salt>$<hash>
        return f"pbkdf2_{self.algo}${self.iterations}${self.salt_b64}${self.hash_b64}"

    @staticmethod
    def parse(value: object) -> "PasswordHash":
        if not isinstance(value, str):
            raise TypeError("Invalid password hash.")

        parts = value.split("$")
        if len(parts) != 4:
            raise ValueError("Invalid password hash.")

        scheme, iterations_text, salt_b64, hash_b64 = parts

        if not scheme.startswith("pbkdf2_"):
            raise ValueError("Invalid password hash.")

        algo = scheme.removeprefix("pbkdf2_")
        if not algo or algo not in hashlib.algorithms_available:
            raise ValueError("Invalid password hash.")

        try:
            iterations = int(iterations_text)
        except ValueError as exc:
            raise ValueError("Invalid password hash.") from exc

        if iterations < 1:
            raise ValueError("Invalid password hash.")

        try:
            salt = base64.b64decode(salt_b64, validate=True)
            hash_value = base64.b64decode(hash_b64, validate=True)
        except binascii.Error as exc:
            raise ValueError("Invalid password hash.") from exc
        if not salt or not hash_value:
            raise ValueError("Invalid password hash.")

        return PasswordHash(
            algo=algo,
            iterations=iterations,
            salt_b64=salt_b64,
            hash_b64=hash_b64,
        )


def hash_password(plain: str) -> PasswordHash:
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
    salt = base64.b64decode(stored.salt_b64)
    dk2 = hashlib.pbkdf2_hmac(stored.algo, plain.encode("utf-8"), salt, stored.iterations)
    return hmac.compare_digest(base64.b64encode(dk2).decode("ascii"), stored.hash_b64)
