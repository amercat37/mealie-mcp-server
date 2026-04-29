import logging
import traceback
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_foods_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all food-related tools with the MCP server."""

    @mcp.tool()
    def get_foods(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all ingredient foods with pagination.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page
            search: Search term to filter foods

        Returns:
            Dict[str, Any]: Foods with pagination information
        """
        try:
            logger.info({"message": "Fetching foods", "page": page, "per_page": per_page, "search": search})
            return mealie.get_foods(page=page, per_page=per_page, search=search)
        except Exception as e:
            error_msg = f"Error fetching foods: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_food(item_id: str) -> Dict[str, Any]:
        """Get a specific ingredient food by ID.

        Args:
            item_id: The UUID of the food item

        Returns:
            Dict[str, Any]: The food details including label and alias information
        """
        try:
            logger.info({"message": "Fetching food", "item_id": item_id})
            return mealie.get_food(item_id)
        except Exception as e:
            error_msg = f"Error fetching food '{item_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)
