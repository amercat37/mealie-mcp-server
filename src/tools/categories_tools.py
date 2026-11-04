import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher
from trim import trim_organizer

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
    def get_category(category_id: str) -> Dict[str, Any]:
        """Get a specific category by ID.

        Args:
            category_id: The UUID of the category

        Returns:
            Dict[str, Any]: The category's id, name and slug, and recipes: the slug of
            every recipe with this category. Use get_recipe_detailed for any recipe's details.
        """
        try:
            logger.info({"message": "Fetching category", "category_id": category_id})
            # Mealie's lookup by id doesn't include the category's recipes, so look up
            # its slug, then fetch by slug, which does
            slug = mealie.get_category(category_id)["slug"]
            return trim_organizer(mealie.get_category_by_slug(slug), with_recipes=True)
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
            Dict[str, Any]: The category's id, name and slug, and recipes: the slug of
            every recipe with this category. Use get_recipe_detailed for any recipe's details.
        """
        try:
            logger.info({"message": "Fetching category by slug", "category_slug": category_slug})
            return trim_organizer(mealie.get_category_by_slug(category_slug), with_recipes=True)
        except Exception as e:
            error_msg = f"Error fetching category by slug '{category_slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_empty_categories() -> List[Dict[str, Any]]:
        """List categories that have no recipes assigned. Use this to find and
        clean up stale or unused category entries.

        Returns:
            List[Dict[str, Any]]: Categories with no associated recipes
        """
        try:
            logger.info({"message": "Fetching empty categories"})
            return mealie.get_empty_categories()
        except Exception as e:
            error_msg = f"Error fetching empty categories: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)


