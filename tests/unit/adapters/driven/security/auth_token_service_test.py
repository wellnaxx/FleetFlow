import unittest
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

from src.adapters.driven.security import auth_token_service
from src.adapters.driven.security.auth_token_service import (
    TokenInput,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    create_token,
    decode_token,
)


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
                    access_secret="x" * 32,
                    refresh_secret="y" * 32,
                    algorithm="HS256",
                    access_token_expire_minutes=15,
                    refresh_token_expire_days=7,
                ),
            ),
            self.assertRaises(KeyError),
        ):
            missing_role: Any = {
                "user_id": 42,
                "username": "alice",
                "token_version": 1,
            }
            create_token(missing_role)

    def test_build_payload_uses_same_base_time_for_iat_and_exp(self) -> None:
        fixed_now = datetime(2026, 5, 18, 12, 0, 0, tzinfo=UTC)
        with (
            patch(
                "src.adapters.driven.security.auth_token_service.load_jwt_config",
                return_value=SimpleNamespace(
                    access_secret="x" * 32,
                    refresh_secret="y" * 32,
                    algorithm="HS256",
                    access_token_expire_minutes=15,
                    refresh_token_expire_days=7,
                ),
            ),
            patch("src.adapters.driven.security.auth_token_service.datetime") as datetime_mock,
        ):
            datetime_mock.now.return_value = fixed_now

            payload = auth_token_service._build_payload(  # type: ignore[reportPrivateUsage]
                {
                    "user_id": 42,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "token_version": 1,
                },
                "access",
            )

        self.assertEqual(payload.iat, int(fixed_now.timestamp()))
        self.assertEqual(payload.exp - payload.iat, 15 * 60)

    def test_access_token_cannot_be_decoded_as_refresh_token(self) -> None:
        config = SimpleNamespace(
            access_secret="a" * 32,
            refresh_secret="b" * 32,
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )

        with patch("src.adapters.driven.security.auth_token_service.load_jwt_config", return_value=config):
            token = create_access_token(
                {
                    "user_id": 42,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "token_version": 1,
                }
            )

            self.assertIsNone(decode_token(token, expected_type="refresh"))

    def test_refresh_token_cannot_be_decoded_as_access_token(self) -> None:
        config = SimpleNamespace(
            access_secret="a" * 32,
            refresh_secret="b" * 32,
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )

        with patch("src.adapters.driven.security.auth_token_service.load_jwt_config", return_value=config):
            token = create_refresh_token(
                {
                    "user_id": 42,
                    "username": "alice",
                    "role": "EMPLOYEE",
                    "token_version": 1,
                }
            )

            self.assertIsNone(decode_token(token, expected_type="access"))

    def test_tokens_decode_with_their_matching_secret(self) -> None:
        config = SimpleNamespace(
            access_secret="a" * 32,
            refresh_secret="b" * 32,
            algorithm="HS256",
            access_token_expire_minutes=15,
            refresh_token_expire_days=7,
        )

        with patch("src.adapters.driven.security.auth_token_service.load_jwt_config", return_value=config):
            token_data: TokenInput = {
                "user_id": 42,
                "username": "alice",
                "role": "EMPLOYEE",
                "token_version": 1,
            }
            access_payload = decode_token(create_access_token(token_data), expected_type="access")
            refresh_payload = decode_token(create_refresh_token(token_data), expected_type="refresh")

        self.assertIsNotNone(access_payload)
        self.assertIsNotNone(refresh_payload)
        assert access_payload is not None
        assert refresh_payload is not None
        self.assertEqual(access_payload.type, "access")
        self.assertEqual(refresh_payload.type, "refresh")
