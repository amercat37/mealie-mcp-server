import logging
import os
import time

import httpx
from authlib.jose import JsonWebKey, jwt
from authlib.jose.errors import JoseError

from mcp.server.auth.provider import AccessToken

logger = logging.getLogger("mealie-mcp.auth")

_discovery_cache: dict[str, str] = {}  # issuer -> jwks_uri
_jwks_cache: dict = {}
_jwks_cached_at: float = 0.0
_JWKS_TTL = 3600  # seconds


async def _get_jwks_uri(issuer: str) -> str:
    if issuer in _discovery_cache:
        return _discovery_cache[issuer]
    discovery_url = f"{issuer}/.well-known/openid-configuration"
    logger.info("Fetching OIDC discovery document from %s", discovery_url)
    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        jwks_uri = data["jwks_uri"]
        _discovery_cache[issuer] = jwks_uri
        logger.info("Discovered JWKS URI: %s", jwks_uri)
        return jwks_uri


async def _get_jwks(jwks_uri: str) -> dict:
    global _jwks_cache, _jwks_cached_at
    now = time.monotonic()
    if _jwks_cache and (now - _jwks_cached_at) < _JWKS_TTL:
        logger.debug("JWKS cache hit (age=%.0fs)", now - _jwks_cached_at)
        return _jwks_cache
    logger.info("Fetching JWKS from %s", jwks_uri)
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()
        _jwks_cached_at = now
        key_count = len(_jwks_cache.get("keys", []))
        logger.info("JWKS fetched successfully (%d key(s))", key_count)
        return _jwks_cache


class AuthentikTokenVerifier:
    """Validates Authentik-issued JWTs for the MCP bearer auth middleware."""

    def __init__(self, issuer: str, audience: str | None = None):
        self._issuer = issuer.rstrip("/")
        self._audience = audience
        logger.info(
            "AuthentikTokenVerifier initialized (issuer=%s, audience=%s)",
            self._issuer,
            audience or "not set",
        )

    async def verify_token(self, token: str) -> AccessToken | None:
        logger.debug("Verifying bearer token")
        try:
            jwks_uri = await _get_jwks_uri(self._issuer)
            jwks_data = await _get_jwks(jwks_uri)
            key_set = JsonWebKey.import_key_set(jwks_data)
            claims = jwt.decode(token, key_set)
            claims.validate_exp()
            claims.validate_iss(self._issuer)
            if self._audience:
                claims.validate_aud(self._audience)
            scopes_raw = claims.get("scope", "")
            scopes = scopes_raw.split() if isinstance(scopes_raw, str) else list(scopes_raw)
            client_id = claims.get("client_id") or claims.get("azp") or claims.get("sub", "")
            exp = claims.get("exp")
            logger.debug("Token valid (client_id=%s, scopes=%s)", client_id, scopes)
            return AccessToken(
                token=token,
                client_id=client_id,
                scopes=scopes,
                expires_at=int(exp) if exp is not None else None,
            )
        except JoseError as e:
            logger.warning("JWT validation failed: %s", e)
            return None
        except httpx.HTTPError as e:
            logger.error("Failed to fetch OIDC discovery or JWKS: %s", e)
            return None
        except Exception as e:
            logger.error("Unexpected error during token verification: %s", e, exc_info=True)
            return None


def build_token_verifier() -> AuthentikTokenVerifier:
    issuer = os.environ["AUTHENTIK_ISSUER"]
    audience = os.environ.get("AUTHENTIK_AUDIENCE")
    return AuthentikTokenVerifier(issuer=issuer, audience=audience)
