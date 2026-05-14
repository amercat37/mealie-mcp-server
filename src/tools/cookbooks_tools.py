import logging
import traceback
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_cookbooks_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all cookbook-related tools with the MCP server."""

    @mcp.tool()
    def get_cookbooks(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all cookbooks (curated recipe collections) in the household.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Cookbooks with pagination information
        """
        try:
            logger.info({"message": "Fetching cookbooks"})
            return mealie.get_cookbooks(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching cookbooks: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)
