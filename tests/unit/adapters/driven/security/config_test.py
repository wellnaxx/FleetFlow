import os
import unittest
from unittest.mock import patch

from src.adapters.driven.security.config import JWTConfig, load_jwt_config


class JWTConfigShould(unittest.TestCase):
    def setUp(self) -> None:
        load_jwt_config.cache_clear()

    def tearDown(self) -> None:
        load_jwt_config.cache_clear()

    def test_loads_separate_access_and_refresh_secrets(self) -> None:
        env = {
            "JWT_ACCESS_SECRET": "a" * 32,
            "JWT_REFRESH_SECRET": "b" * 32,
            "JWT_ALGORITHM": "HS512",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "JWT_REFRESH_TOKEN_EXPIRE_DAYS": "14",
        }

        with patch.dict(os.environ, env, clear=True), patch("src.adapters.driven.security.config.load_dotenv"):
            config = load_jwt_config()

        self.assertEqual(
            config,
            JWTConfig(
                access_secret="a" * 32,
                refresh_secret="b" * 32,
                algorithm="HS512",
                access_token_expire_minutes=30,
                refresh_token_expire_days=14,
            ),
        )

    def test_requires_access_secret(self) -> None:
        env = {"JWT_REFRESH_SECRET": "b" * 32}

        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.adapters.driven.security.config.load_dotenv"),
            self.assertRaises(RuntimeError) as ctx,
        ):
            load_jwt_config()

        self.assertIn("JWT_ACCESS_SECRET is required", str(ctx.exception))
        self.assertIn("random", str(ctx.exception))

    def test_requires_refresh_secret(self) -> None:
        env = {"JWT_ACCESS_SECRET": "a" * 32}

        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.adapters.driven.security.config.load_dotenv"),
            self.assertRaises(RuntimeError) as ctx,
        ):
            load_jwt_config()

        self.assertIn("JWT_REFRESH_SECRET is required", str(ctx.exception))
        self.assertIn("random", str(ctx.exception))

    def test_rejects_short_access_secret(self) -> None:
        env = {
            "JWT_ACCESS_SECRET": "short",
            "JWT_REFRESH_SECRET": "b" * 32,
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.adapters.driven.security.config.load_dotenv"),
            self.assertRaises(RuntimeError) as ctx,
        ):
            load_jwt_config()

        self.assertIn("JWT_ACCESS_SECRET must be at least 32 characters", str(ctx.exception))
        self.assertIn("not a human-chosen phrase", str(ctx.exception))

    def test_rejects_short_refresh_secret(self) -> None:
        env = {
            "JWT_ACCESS_SECRET": "a" * 32,
            "JWT_REFRESH_SECRET": "short",
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.adapters.driven.security.config.load_dotenv"),
            self.assertRaises(RuntimeError) as ctx,
        ):
            load_jwt_config()

        self.assertIn("JWT_REFRESH_SECRET must be at least 32 characters", str(ctx.exception))
        self.assertIn("not a human-chosen phrase", str(ctx.exception))

    def test_rejects_equal_access_and_refresh_secrets(self) -> None:
        secret = "x" * 32
        env = {
            "JWT_ACCESS_SECRET": secret,
            "JWT_REFRESH_SECRET": secret,
        }

        with (
            patch.dict(os.environ, env, clear=True),
            patch("src.adapters.driven.security.config.load_dotenv"),
            self.assertRaises(RuntimeError) as ctx,
        ):
            load_jwt_config()

        self.assertIn("must be different randomly generated values", str(ctx.exception))
