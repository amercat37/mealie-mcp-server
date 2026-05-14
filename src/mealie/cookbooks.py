import logging
from typing import Any, Dict

from utils import format_api_params

logger = logging.getLogger("mealie-mcp")


class CookbooksMixin:
    """Mixin class for cookbook-related API endpoints"""

    def get_cookbooks(
        self,
        page: int = None,
        per_page: int = None,
    ) -> Dict[str, Any]:
        """Get all cookbooks for the current household.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            JSON response containing cookbooks and pagination information
        """
        params = format_api_params({"page": page, "perPage": per_page})
        logger.info({"message": "Retrieving cookbooks"})
        return self._handle_request("GET", "/api/households/cookbooks", params=params)
