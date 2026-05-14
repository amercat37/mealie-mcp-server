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

    @mcp.tool()
    def get_empty_foods() -> Dict[str, Any]:
        """List foods in the library that are not referenced by any recipe ingredient.
        Use this to find and clean up stale or duplicate food entries.

        Returns:
            Dict[str, Any]: Unused food entries
        """
        try:
            logger.info({"message": "Fetching empty foods"})
            return mealie.get_empty_foods()
        except Exception as e:
            error_msg = f"Error fetching empty foods: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_food(name: str, label_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a new food to the ingredient food library.

        Only call this after confirming the food does not already exist — search
        with get_foods first and check for close name matches before creating.

        Args:
            name: Name of the food (e.g., "chicken breast", "basmati rice")
            label_id: Optional UUID of the shopping list label to pre-assign
                (use get_labels to find label IDs)

        Returns:
            Dict[str, Any]: The created food entry
        """
        try:
            logger.info({"message": "Creating food", "name": name})
            return mealie.create_food(name, label_id=label_id)
        except Exception as e:
            error_msg = f"Error creating food '{name}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def merge_foods(from_food_id: str, to_food_id: str) -> Dict[str, Any]:
        """Merge a duplicate food entry into a canonical one.

        All recipe references to the source food are updated to the target food,
        then the source entry is deleted. Use this to consolidate near-duplicates
        like "chicken breast" and "chicken breasts".

        Use get_foods to find the UUIDs for both foods before calling this.

        Args:
            from_food_id: UUID of the food to merge away (will be deleted)
            to_food_id: UUID of the food to keep as the canonical entry

        Returns:
            Dict[str, Any]: Confirmation of the merge
        """
        try:
            logger.info({"message": "Merging foods", "from": from_food_id, "to": to_food_id})
            return mealie.merge_foods(from_food_id, to_food_id)
        except Exception as e:
            error_msg = f"Error merging foods: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)
