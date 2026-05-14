import logging
import traceback
from typing import Any, Dict, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_organizers_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all organizer-related tools with the MCP server."""

    @mcp.tool()
    def get_cooking_tools(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all cooking tools used to tag which equipment a recipe requires
        (e.g. stand mixer, instant pot, grill).

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Cooking tools with pagination information
        """
        try:
            logger.info({"message": "Fetching cooking tools"})
            return mealie.get_organizer_tools(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching cooking tools: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_units(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all units of measurement used in recipe ingredient quantities
        (e.g. cup, tbsp, grams).

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Units with pagination information
        """
        try:
            logger.info({"message": "Fetching units of measurement"})
            return mealie.get_organizer_units(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching units: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_labels(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """List all shopping list labels used to categorize and sort shopping items
        by store section (e.g. Produce, Dairy & Eggs, Meats).

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Labels with pagination information
        """
        try:
            logger.info({"message": "Fetching shopping list labels"})
            return mealie.get_organizer_labels(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching labels: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)
