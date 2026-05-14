from functools import lru_cache

import httpx
from jose import JWTError, jwk, jwt
from jose.utils import base64url_decode

from app.core.config import settings

_JWKS_URL = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _get_jwks() -> dict:
    resp = httpx.get(_JWKS_URL, timeout=10)
    resp.raise_for_status()
    return resp.json()


def decode_supabase_jwt(token: str) -> dict:
    """Valida JWT Supabase (ES256 via JWKS ou HS256 fallback) e retorna payload."""
    header = jwt.get_unverified_header(token)
    alg = header.get("alg", "")
    kid = header.get("kid")

    if alg == "ES256":
        jwks = _get_jwks()
        keys = jwks.get("keys", [])
        key_data = next((k for k in keys if k.get("kid") == kid), None) or (keys[0] if keys else None)
        if not key_data:
            raise JWTError("Nenhuma chave JWKS encontrada para validar o token")
        public_key = jwk.construct(key_data, algorithm="ES256")
        return jwt.decode(
            token,
            public_key,
            algorithms=["ES256"],
            options={"verify_aud": False},
        )

    # fallback HS256 (tokens de teste gerados localmente)
    return jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        options={"verify_aud": False},
    )


def extract_user_id(token: str) -> str:
    """Retorna o user_id (claim 'sub') do JWT. Lança JWTError se inválido."""
    payload = decode_supabase_jwt(token)
    user_id: str | None = payload.get("sub")
    if not user_id:
        raise JWTError("Token sem claim 'sub'")
    return user_id
