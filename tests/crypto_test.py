import base64
import unittest
from typing import Any
from unittest.mock import patch

from adapters.driven.security.password_hasher import (
    PasswordHash,
    hash_password,
    verify_password,
)


class Crypto_Should(unittest.TestCase):
    def _b64(self, b: bytes) -> str:
        return base64.b64encode(b).decode("ascii")

    @patch("adapters.driven.security.password_hasher.os.urandom", return_value=b"SALT" * 4)  # 16 bytes
    @patch("adapters.driven.security.password_hasher.PBKDF2_ITERATIONS", 100)  # speed up
    def test_hash_password_generates_expected_shape_and_min_len(self, *_: Any) -> None:
        ph = hash_password("CorrectHorse1")
        self.assertEqual(ph.algo, "sha256")
        self.assertIsInstance(ph.iterations, int)
        self.assertGreaterEqual(ph.iterations, 100)
        # salt is our mocked 16 bytes
        self.assertEqual(base64.b64decode(ph.salt_b64), b"SALT" * 4)
        # hash field is base64
        base64.b64decode(ph.hash_b64)  # will raise if not valid b64

        with self.assertRaises(ValueError):
            hash_password("short7")  # too short
        with self.assertRaises(TypeError):
            hash_password(12345678)  # type: ignore[reportArgumentType]  # not a str

    @patch("adapters.driven.security.password_hasher.os.urandom", return_value=b"A" * 16)
    @patch("adapters.driven.security.password_hasher.PBKDF2_ITERATIONS", 50)
    def test_hash_password_different_salts_produce_different_hashes(self, *_: Any) -> None:
        ph1 = hash_password("SamePassword123")
        # change salt:
        with patch("adapters.driven.security.password_hasher.os.urandom", return_value=b"B" * 16):
            ph2 = hash_password("SamePassword123")
        self.assertNotEqual(ph1.hash_b64, ph2.hash_b64)
        self.assertNotEqual(ph1.salt_b64, ph2.salt_b64)

    @patch("adapters.driven.security.password_hasher.os.urandom", return_value=b"\xff" * 16)  # fixed salt
    @patch("adapters.driven.security.password_hasher.PBKDF2_ITERATIONS", 100)  # fast & deterministic
    def test_verify_password_true_and_false(self, *_: Any) -> None:
        # Create a stored hash with the fixed salt + small iteration count
        ph = hash_password("Password123")
        # Correct password must verify
        self.assertTrue(verify_password("Password123", ph))
        # Wrong password must fail (different derived key)
        self.assertFalse(verify_password("WrongPass123", ph))

    @patch("adapters.driven.security.password_hasher.hmac.compare_digest", return_value=True)
    @patch("adapters.driven.security.password_hasher.hashlib.pbkdf2_hmac", return_value=b"\x11" * 32)
    def test_verify_password_uses_compare_digest(self, pbkdf2_mock: Any, cd_mock: Any) -> None:
        stored = PasswordHash(
            algo="sha256",
            iterations=123,
            salt_b64=self._b64(b"S" * 16),
            hash_b64=self._b64(b"\x11" * 32),
        )
        ok = verify_password("any-pass", stored)
        self.assertTrue(ok)
        cd_mock.assert_called_once()  # timing-safe compare is used
        # ensure pbkdf2_hmac called with stored.algo & iterations
        args, _kwargs = pbkdf2_mock.call_args
        self.assertEqual(args[0], "sha256")
        self.assertEqual(args[3], 123)

    def test_passwordhash_serialize_and_parse_roundtrip(self) -> None:
        ph = PasswordHash(
            algo="sha256",
            iterations=200000,
            salt_b64=self._b64(b"X" * 16),
            hash_b64=self._b64(b"Y" * 32),
        )
        s = ph.serialize()
        ph2 = PasswordHash.parse(s)
        self.assertEqual(ph2, ph)

    def test_parse_malformed_raises(self) -> None:
        with self.assertRaises(ValueError):
            # Missing parts -> split will produce < 4 items and raise
            PasswordHash.parse("pbkdf2_sha256$200000$only-two-parts")
