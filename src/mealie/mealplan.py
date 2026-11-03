import logging
from datetime import date as Date
from datetime import timedelta
from typing import Any, Dict, List, Optional

from utils import format_api_params

logger = logging.getLogger("mealie-mcp")


class MealplanMixin:
    """Mixin class for mealplan-related API endpoints"""

    def get_mealplans(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        include_week_entries: bool = True,
    ) -> Dict[str, Any]:
        """Get all mealplans for the current household with pagination.

        Args:
            start_date: Start date for filtering meal plans (ISO format YYYY-MM-DD)
            end_date: End date for filtering meal plans (ISO format YYYY-MM-DD)
            page: Page number to retrieve
            per_page: Number of items per page
            include_week_entries: Include whole-week entries (Mealie v3.30+ hides them
                unless asked). A week entry overlapping the date range is included.

        Returns:
            JSON response containing mealplan items and pagination information

        Raises:
            MealieApiError: If the API request fails
        """
        # Mealie reads these date filters by their snake_case names; the camelCase
        # names were silently ignored, returning every entry.
        param_dict = {
            "start_date": start_date,
            "end_date": end_date,
            "include_week_entries": include_week_entries,
            "page": page,
            "perPage": per_page,
        }

        params = format_api_params(param_dict)

        logger.info({"message": "Retrieving mealplans", "parameters": params})
        response = self._handle_request(
            "GET", "/api/households/mealplans", params=params
        )
        return response

    def get_household_preferences(self) -> Dict[str, Any]:
        """Get the current household's preferences (e.g. firstDayOfWeek)."""
        return self._handle_request("GET", "/api/households/preferences")

    def week_range(self, day: str) -> tuple[str, str]:
        """(start, end) dates of the week containing `day`, as Mealie's planner shows it.

        The week starts on the household's firstDayOfWeek preference (0=Sunday ...
        6=Saturday). Mealie only accepts week entries whose end date is exactly six
        days after their start date.
        """
        d = Date.fromisoformat(day)
        first = self.get_household_preferences().get("firstDayOfWeek") or 0
        # date.weekday() is Monday=0; Mealie's firstDayOfWeek is Sunday=0
        offset = ((d.weekday() + 1) % 7 - first) % 7
        start = d - timedelta(days=offset)
        return start.isoformat(), (start + timedelta(days=6)).isoformat()

    def create_mealplan(
        self,
        date: str,
        recipe_id: Optional[str] = None,
        title: Optional[str] = None,
        entry_type: str = "breakfast",
        whole_week: bool = False,
    ) -> Dict[str, Any]:
        """Create a new mealplan entry.

        Args:
            date: Date for the mealplan in ISO format (YYYY-MM-DD)
            recipe_id: UUID of the recipe to add to the mealplan (optional)
            title: Title for the mealplan entry if not using a recipe (optional)
            entry_type: Type of mealplan entry (breakfast, lunch, dinner, etc.)
            whole_week: Plan it for the whole week containing `date` rather than that day

        Returns:
            JSON response containing the created mealplan entry

        Raises:
            ValueError: If neither recipe_id nor title is provided
            MealieApiError: If the API request fails
        """
        if not recipe_id and not title:
            raise ValueError("Either recipe_id or title must be provided")
        if not date:
            raise ValueError("Date cannot be empty")

        # Build the request payload
        payload = {
            "date": date,
            "entryType": entry_type,
        }
        if whole_week:
            payload["date"], payload["endDate"] = self.week_range(date)

        if recipe_id:
            payload["recipeId"] = recipe_id
        if title:
            payload["title"] = title

        logger.info(
            {
                "message": "Creating mealplan entry",
                "date": date,
                "entry_type": entry_type,
            }
        )
        return self._handle_request("POST", "/api/households/mealplans", json=payload)

    def get_todays_mealplan(self) -> List[Dict[str, Any]]:
        """Get the mealplan entries for today.

        Returns:
            List of today's mealplan entries

        Raises:
            MealieApiError: If the API request fails
        """
        logger.info({"message": "Retrieving today's mealplan"})
        return self._handle_request("GET", "/api/households/mealplans/today")

    def update_mealplan(
        self,
        entry_id: str,
        date: str,
        entry_type: str,
        recipe_id: Optional[str] = None,
        title: Optional[str] = None,
        whole_week: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update an existing mealplan entry.

        Args:
            entry_id: UUID of the mealplan entry to update
            date: New date for the entry (YYYY-MM-DD)
            entry_type: Type of entry (breakfast, lunch, dinner, side)
            recipe_id: UUID of the recipe (optional)
            title: Title for non-recipe entries (optional)
            whole_week: True makes it a whole-week entry, False a single-day entry;
                None keeps the entry's current kind

        Returns:
            JSON response containing the updated mealplan entry
        """
        if not entry_id:
            raise ValueError("Entry ID cannot be empty")
        if not date:
            raise ValueError("Date cannot be empty")

        logger.info({"message": "Updating mealplan entry", "entry_id": entry_id})
        current = self._handle_request("GET", f"/api/households/mealplans/{entry_id}")
        updates: Dict[str, Any] = {"date": date, "entryType": entry_type, "endDate": None}
        if whole_week is None:
            whole_week = bool(current.get("endDate"))  # keep the entry's current kind
        if whole_week:
            # Recompute both ends: Mealie rejects a week entry whose end date isn't
            # exactly six days after its (possibly moved) start date.
            updates["date"], updates["endDate"] = self.week_range(date)
        if recipe_id:
            updates["recipeId"] = recipe_id
        if title:
            updates["title"] = title
        merged = {**current, **updates}
        return self._handle_request("PUT", f"/api/households/mealplans/{entry_id}", json=merged)

    def delete_mealplan(self, entry_id: str) -> Dict[str, Any]:
        """Delete a mealplan entry.

        Args:
            entry_id: UUID of the mealplan entry to delete

        Returns:
            JSON response confirming deletion
        """
        if not entry_id:
            raise ValueError("Entry ID cannot be empty")

        logger.info({"message": "Deleting mealplan entry", "entry_id": entry_id})
        return self._handle_request("DELETE", f"/api/households/mealplans/{entry_id}")
