import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src.adapters.driven.security.auth_token_service import TokenPayload, create_token


class TokenPayloadShould(unittest.TestCase):
    def valid_payload(self) -> dict[str, object]:
        return {
            "sub": "42",
            "iat": 1_700_000_000,
            "exp": 1_700_000_900,
            "jti": "token-id",
            "type": "access",
            "username": "alice",
            "role": "EMPLOYEE",
            "token_version": 1,
        }

    def test_from_dict_accepts_valid_payload(self) -> None:
        payload = TokenPayload.from_dict(self.valid_payload())

        self.assertEqual(
            payload,
            TokenPayload(
                sub="42",
                iat=1_700_000_000,
                exp=1_700_000_900,
                jti="token-id",
                type="access",
                username="alice",
                role="EMPLOYEE",
                token_version=1,
            ),
        )

    def test_from_dict_rejects_bool_numeric_claims(self) -> None:
        for field in ("iat", "exp", "token_version"):
            with self.subTest(field=field):
                raw = self.valid_payload()
                raw[field] = True

                self.assertIsNone(TokenPayload.from_dict(raw))

    def test_from_dict_rejects_non_positive_or_negative_numeric_claims(self) -> None:
        cases = {
            "iat": -1,
            "exp": -1,
            "token_version": 0,
        }
        for field, value in cases.items():
            with self.subTest(field=field):
                raw = self.valid_payload()
                raw[field] = value

                self.assertIsNone(TokenPayload.from_dict(raw))

    def test_from_dict_rejects_blank_string_claims(self) -> None:
        for field in ("sub", "username", "role"):
            with self.subTest(field=field):
                raw = self.valid_payload()
                raw[field] = "   "

                self.assertIsNone(TokenPayload.from_dict(raw))

    def test_create_token_requires_role(self) -> None:
        with (
            patch(
                "src.adapters.driven.security.auth_token_service.load_jwt_config",
                return_value=SimpleNamespace(
                    secret="x" * 32,
                    algorithm="HS256",
                    access_token_expire_minutes=15,
                    refresh_token_expire_days=7,
                ),
            ),
            self.assertRaises(KeyError),
        ):
            create_token(  # type: ignore[typeddict-item]
                {
                    "user_id": 42,
                    "username": "alice",
                    "token_version": 1,
                }
            )
