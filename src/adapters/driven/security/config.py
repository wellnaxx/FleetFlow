from dataclasses import dataclass
from functools import lru_cache

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var


@dataclass(frozen=True, slots=True)
class JWTConfig:
    access_secret: str
    refresh_secret: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int


def _load_secret(name: str) -> str:
    secret = get_env_var(name, "")
    if not secret:
        raise RuntimeError(f"{name} is required. Generate it with a cryptographically random source.")
    if len(secret) < 32:
        raise RuntimeError(
            f"{name} must be at least 32 characters long and randomly generated, not a human-chosen phrase."
        )
    return secret


@lru_cache(maxsize=1)
def load_jwt_config() -> JWTConfig:
    load_dotenv()

    access_secret = _load_secret("JWT_ACCESS_SECRET")
    refresh_secret = _load_secret("JWT_REFRESH_SECRET")
    if access_secret == refresh_secret:
        raise RuntimeError(
            "JWT_ACCESS_SECRET and JWT_REFRESH_SECRET must be different randomly generated values."
        )

    return JWTConfig(
        access_secret=access_secret,
        refresh_secret=refresh_secret,
        algorithm=get_env_var("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(get_env_var("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        refresh_token_expire_days=int(get_env_var("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    )
