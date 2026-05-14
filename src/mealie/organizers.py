import logging
from typing import Any, Dict, Optional

from utils import format_api_params

logger = logging.getLogger("mealie-mcp")


class OrganizersMixin:
    """Mixin class for organizer-related API endpoints (tools, units, labels)"""

    def get_organizer_tools(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all cooking tools.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing cooking tools and pagination information
        """
        params = format_api_params({"page": page, "perPage": per_page})
        logger.info({"message": "Retrieving cooking tools"})
        return self._handle_request("GET", "/api/organizers/tools", params=params)

    def get_organizer_units(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all units of measurement.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing units and pagination information
        """
        params = format_api_params({"page": page, "perPage": per_page})
        logger.info({"message": "Retrieving units of measurement"})
        return self._handle_request("GET", "/api/units", params=params)

    def get_organizer_labels(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all shopping list labels.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing labels and pagination information
        """
        params = format_api_params({"page": page, "perPage": per_page})
        logger.info({"message": "Retrieving shopping list labels"})
        return self._handle_request("GET", "/api/groups/labels", params=params)
