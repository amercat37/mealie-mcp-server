import logging
from typing import Any, Dict, Optional

from utils import format_api_params

logger = logging.getLogger("mealie-mcp")


class FoodsMixin:
    """Mixin class for ingredient food-related API endpoints"""

    def get_foods(
        self,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        search: Optional[str] = None,
        query_filter: Optional[str] = None,
        order_by_null_position: Optional[str] = None,
        pagination_seed: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all ingredient foods.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page
            order_by: Field to order results by
            order_direction: Direction to order results ('asc' or 'desc')
            search: Search term to filter foods
            query_filter: Advanced query filter
            order_by_null_position: How to handle nulls in ordering ('first' or 'last')
            pagination_seed: Seed for consistent pagination

        Returns:
            JSON response containing food items and pagination information
        """
        param_dict = {
            "page": page,
            "perPage": per_page,
            "orderBy": order_by,
            "orderDirection": order_direction,
            "search": search,
            "queryFilter": query_filter,
            "orderByNullPosition": order_by_null_position,
            "paginationSeed": pagination_seed,
        }

        params = format_api_params(param_dict)

        logger.info({"message": "Retrieving foods", "parameters": params})
        return self._handle_request("GET", "/api/foods", params=params)

    def get_food(self, item_id: str) -> Dict[str, Any]:
        """Get a specific ingredient food by ID.

        Args:
            item_id: The UUID of the food item

        Returns:
            JSON response containing the food details
        """
        if not item_id:
            raise ValueError("Food item ID cannot be empty")

        logger.info({"message": "Retrieving food", "item_id": item_id})
        return self._handle_request("GET", f"/api/foods/{item_id}")

    def get_empty_foods(self) -> Dict[str, Any]:
        """Get foods not referenced by any recipe ingredient.

        Returns:
            JSON response containing unused food entries
        """
        logger.info({"message": "Retrieving empty foods"})
        return self._handle_request("GET", "/api/foods/empty")

    def create_food(self, name: str, label_id: Optional[str] = None) -> Dict[str, Any]:
        """Add a new food to the ingredient food library.

        Args:
            name: Name of the food
            label_id: Optional UUID of the shopping list label to associate

        Returns:
            JSON response containing the created food
        """
        if not name:
            raise ValueError("Food name cannot be empty")

        payload: Dict[str, Any] = {"name": name}
        if label_id:
            payload["labelId"] = label_id

        logger.info({"message": "Creating food", "name": name})
        return self._handle_request("POST", "/api/foods", json=payload)

    def merge_foods(self, from_food_id: str, to_food_id: str) -> Dict[str, Any]:
        """Merge a duplicate food entry into a canonical one.

        All recipe references to from_food_id are updated to to_food_id,
        then the source entry is deleted.

        Args:
            from_food_id: UUID of the food to merge away (will be deleted)
            to_food_id: UUID of the food to keep as canonical

        Returns:
            JSON response confirming the merge
        """
        if not from_food_id:
            raise ValueError("Source food ID cannot be empty")
        if not to_food_id:
            raise ValueError("Target food ID cannot be empty")

        payload = {"fromFood": from_food_id, "toFood": to_food_id}

        logger.info({"message": "Merging foods", "from": from_food_id, "to": to_food_id})
        return self._handle_request("PUT", "/api/foods/merge", json=payload)

    def delete_food(self, food_id: str) -> Dict[str, Any]:
        """Delete a food entry from the ingredient library.

        Args:
            food_id: UUID of the food to delete

        Returns:
            JSON response confirming deletion
        """
        if not food_id:
            raise ValueError("Food ID cannot be empty")

        logger.info({"message": "Deleting food", "food_id": food_id})
        return self._handle_request("DELETE", f"/api/foods/{food_id}")
