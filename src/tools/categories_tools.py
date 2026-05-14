import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_categories_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all category-related tools with the MCP server."""

    @mcp.tool()
    def get_categories(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all recipe categories with pagination.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Categories with pagination information
        """
        try:
            logger.info({"message": "Fetching categories", "page": page, "per_page": per_page})
            return mealie.get_categories(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching categories: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_empty_categories() -> List[Dict[str, Any]]:
        """Get all categories that have no recipes assigned.

        Returns:
            List[Dict[str, Any]]: List of empty categories
        """
        try:
            logger.info({"message": "Fetching empty categories"})
            return mealie.get_empty_categories()
        except Exception as e:
            error_msg = f"Error fetching empty categories: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_category(category_id: str) -> Dict[str, Any]:
        """Get a specific category by ID.

        Args:
            category_id: The UUID of the category

        Returns:
            Dict[str, Any]: The category details including associated recipes
        """
        try:
            logger.info({"message": "Fetching category", "category_id": category_id})
            return mealie.get_category(category_id)
        except Exception as e:
            error_msg = f"Error fetching category '{category_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_category_by_slug(category_slug: str) -> Dict[str, Any]:
        """Get a specific category by its slug.

        Args:
            category_slug: The slug of the category (e.g., "breakfast", "desserts")

        Returns:
            Dict[str, Any]: The category details including associated recipes
        """
        try:
            logger.info({"message": "Fetching category by slug", "category_slug": category_slug})
            return mealie.get_category_by_slug(category_slug)
        except Exception as e:
            error_msg = f"Error fetching category by slug '{category_slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)


