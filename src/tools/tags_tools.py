import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher

logger = logging.getLogger("mealie-mcp")


def register_tags_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all tag-related tools with the MCP server."""

    @mcp.tool()
    def get_tags(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all recipe tags with pagination.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Tags with pagination information
        """
        try:
            logger.info({"message": "Fetching tags", "page": page, "per_page": per_page})
            return mealie.get_tags(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching tags: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_empty_tags() -> List[Dict[str, Any]]:
        """Get all tags that have no recipes assigned.

        Returns:
            List[Dict[str, Any]]: List of empty tags
        """
        try:
            logger.info({"message": "Fetching empty tags"})
            return mealie.get_empty_tags()
        except Exception as e:
            error_msg = f"Error fetching empty tags: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_tag(tag_id: str) -> Dict[str, Any]:
        """Get a specific tag by ID.

        Args:
            tag_id: The UUID of the tag

        Returns:
            Dict[str, Any]: The tag details including associated recipes
        """
        try:
            logger.info({"message": "Fetching tag", "tag_id": tag_id})
            return mealie.get_tag(tag_id)
        except Exception as e:
            error_msg = f"Error fetching tag '{tag_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_tag_by_slug(tag_slug: str) -> Dict[str, Any]:
        """Get a specific tag by its slug.

        Args:
            tag_slug: The slug of the tag (e.g., "quick", "healthy")

        Returns:
            Dict[str, Any]: The tag details including associated recipes
        """
        try:
            logger.info({"message": "Fetching tag by slug", "tag_slug": tag_slug})
            return mealie.get_tag_by_slug(tag_slug)
        except Exception as e:
            error_msg = f"Error fetching tag by slug '{tag_slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)


