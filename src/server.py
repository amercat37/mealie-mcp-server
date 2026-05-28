import logging
import os
import traceback

import httpx
from dotenv import load_dotenv
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from auth import build_token_verifier
from mealie import MealieFetcher
from prompts import register_prompts
from tools import register_all_tools

# Load environment variables first
load_dotenv()

# Get log level from environment variable with INFO as default
log_level_name = os.getenv("LOG_LEVEL", "INFO")
log_level = getattr(logging, log_level_name.upper(), logging.INFO)

# Configure logging
logging.basicConfig(
    level=log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("mealie_mcp_server.log")],
)
logger = logging.getLogger("mealie-mcp")

_authentik_issuer = os.getenv("AUTHENTIK_ISSUER")
_auth_settings = None
_token_verifier = None
if _authentik_issuer:
    _auth_settings = AuthSettings(
        issuer_url=_authentik_issuer,
        resource_server_url=os.environ["MCP_SERVER_URL"],
    )
    _token_verifier = build_token_verifier()

mcp = FastMCP(
    "mealie",
    host="0.0.0.0",
    port=8000,
    auth=_auth_settings,
    token_verifier=_token_verifier,
)

_oidc_metadata_cache: dict | None = None


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def oauth_authorization_server_metadata(request: Request) -> Response:
    """Proxy Authentik's OIDC discovery so clients that skip oauth-protected-resource still find the token endpoint."""
    global _oidc_metadata_cache
    if _oidc_metadata_cache is None:
        issuer = (_authentik_issuer or "").rstrip("/")
        discovery_url = f"{issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            resp = await client.get(discovery_url, timeout=10)
            resp.raise_for_status()
            _oidc_metadata_cache = resp.json()
        logger.info("Cached OAuth authorization server metadata from %s", discovery_url)
    return JSONResponse(_oidc_metadata_cache)


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration(request: Request) -> Response:
    return await oauth_authorization_server_metadata(request)


MEALIE_BASE_URL = os.getenv("MEALIE_BASE_URL")
MEALIE_API_KEY = os.getenv("MEALIE_API_KEY")
if not MEALIE_BASE_URL or not MEALIE_API_KEY:
    raise ValueError(
        "MEALIE_BASE_URL and MEALIE_API_KEY must be set in environment variables."
    )

try:
    mealie = MealieFetcher(
        base_url=MEALIE_BASE_URL,
        api_key=MEALIE_API_KEY,
    )
except Exception as e:
    logger.error({"message": "Failed to initialize Mealie client", "error": str(e)})
    logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
    raise

register_prompts(mcp)
register_all_tools(mcp, mealie)

if __name__ == "__main__":
    try:
        logger.info({"message": "Starting Mealie MCP Server"})
        mcp.run(transport="streamable-http")
    except Exception as e:
        logger.critical(
            {"message": "Fatal error in Mealie MCP Server", "error": str(e)}
        )
        logger.debug(
            {"message": "Error traceback", "traceback": traceback.format_exc()}
        )
        raise
