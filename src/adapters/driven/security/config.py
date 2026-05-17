from dataclasses import dataclass

from dotenv import load_dotenv

from src.shared.env_vars import get_env_var


@dataclass(frozen=True)
class JWTConfig:
    secret: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int


def load_jwt_config() -> JWTConfig:
    load_dotenv()

    secret = get_env_var("JWT_SECRET", "")
    if not secret:
        raise RuntimeError("JWT_SECRET is required.")
    if len(secret) < 32:
        raise RuntimeError("JWT_SECRET must be at least 32 characters long for security.")

    return JWTConfig(
        secret=secret,
        algorithm=get_env_var("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(get_env_var("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "15")),
        refresh_token_expire_days=int(get_env_var("JWT_REFRESH_TOKEN_EXPIRE_DAYS", "7")),
    )
