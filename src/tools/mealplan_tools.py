import logging
import traceback
import uuid
from datetime import date as Date
from typing import Any, Dict, List, Optional, Union

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from pydantic import ValidationError

from mealie import MealieFetcher
from models.mealplan import MealPlanEntry

logger = logging.getLogger("mealie-mcp")

ENTRY_TYPES = ("breakfast", "lunch", "dinner", "side", "snack", "drink", "dessert")


def entry_problem(entry: MealPlanEntry) -> Optional[str]:
    """Why Mealie would reject this entry, or None — checked before creating anything."""
    try:
        Date.fromisoformat(entry.date)
    except (TypeError, ValueError):
        return f'date "{entry.date}" is not YYYY-MM-DD'
    if entry.entry_type not in ENTRY_TYPES:
        return f'entry_type "{entry.entry_type}" must be one of: {", ".join(ENTRY_TYPES)}'
    if not entry.recipe_id and not entry.title:
        return "needs a recipe_id or a title"
    if entry.recipe_id:
        try:
            uuid.UUID(str(entry.recipe_id))
        except ValueError:
            return f'recipe_id "{entry.recipe_id}" is not a recipe UUID'
    return None


def field_error(err: Dict[str, Any]) -> str:
    """A pydantic error on a bulk entry, worded for the assistant."""
    field = err["loc"][0] if err["loc"] else "entry"
    if err["type"] == "extra_forbidden":
        return f'unknown field "{field}" (fields are: {", ".join(MealPlanEntry.model_fields)})'
    if err["type"] == "missing":
        if field == "entry_type":
            return f'missing "entry_type" (one of: {", ".join(ENTRY_TYPES)})'
        return f'missing "{field}"'
    return f"{'.'.join(str(part) for part in err['loc']) or 'entry'}: {err['msg']}"


def summarize_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """A meal plan entry without the embedded recipe summary: id, date, endDate (week
    entries), entryType, title, text (the entry's note, set in Mealie), and recipeId /
    recipeName / recipeSlug for a recipe entry. Empty fields are left out."""
    summary: Dict[str, Any] = {"id": entry.get("id"), "date": entry.get("date")}
    if entry.get("endDate"):
        summary["endDate"] = entry["endDate"]
    summary["entryType"] = entry.get("entryType")
    if entry.get("title"):
        summary["title"] = entry["title"]
    if entry.get("text"):
        summary["text"] = entry["text"]
    if entry.get("recipeId"):
        recipe = entry.get("recipe") or {}
        summary["recipeId"] = entry["recipeId"]
        summary["recipeName"] = recipe.get("name")
        summary["recipeSlug"] = recipe.get("slug")
    return summary


def register_mealplan_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all mealplan-related tools with the MCP server."""

    @mcp.tool()
    def get_all_mealplans(
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all meal plans for the current household with pagination.

        Includes whole-week entries: an entry with an endDate is planned for the week
        from date to endDate rather than a specific day ("dinner sometime this week").
        A week entry overlapping the date range is included. Use get_recipe_concise or
        get_recipe_detailed with an entry's recipeSlug for the recipe itself.

        Args:
            start_date: Start date for filtering meal plans (ISO format YYYY-MM-DD)
            end_date: End date for filtering meal plans (ISO format YYYY-MM-DD)
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Pagination fields and items: each entry's id, date, endDate
                (week entries), entryType, title, text (its note, if any), and recipeId /
                recipeName / recipeSlug for a recipe entry
        """
        try:
            logger.info(
                {
                    "message": "Fetching mealplans",
                    "start_date": start_date,
                    "end_date": end_date,
                    "page": page,
                    "per_page": per_page,
                }
            )
            result = mealie.get_mealplans(
                start_date=start_date,
                end_date=end_date,
                page=page,
                per_page=per_page,
            )
            if isinstance(result, dict) and isinstance(result.get("items"), list):
                result = {**result, "items": [summarize_entry(e) for e in result["items"]]}
            return result
        except Exception as e:
            error_msg = f"Error fetching mealplans: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    def create_mealplan(
        date: str,
        entry_type: str,
        recipe_id: Optional[str] = None,
        title: Optional[str] = None,
        whole_week: bool = False,
    ) -> Dict[str, Any]:
        """Create a new meal plan entry.

        Args:
            date: Date for the mealplan in ISO format (YYYY-MM-DD)
            entry_type: Type of mealplan entry, required (breakfast, lunch, dinner,
                side, snack, drink, dessert). If the user didn't say which meal, ask.
            recipe_id: UUID of the recipe to add to the mealplan (optional)
            title: Title for the mealplan entry if not using a recipe (optional)
            whole_week: Plan it for the whole week containing `date` instead of that
                day ("dinner sometime this week"). The week follows the household's
                first-day-of-week setting in Mealie.

        Returns:
            Dict[str, Any]: The created entry: id (use it with update_mealplan and
                delete_mealplan), date, endDate (week entries only), entryType, title,
                text (its note, if any) and recipeId/recipeName/recipeSlug
        """
        try:
            logger.info(
                {
                    "message": "Creating mealplan entry",
                    "date": date,
                    "recipe_id": recipe_id,
                    "title": title,
                    "entry_type": entry_type,
                    "whole_week": whole_week,
                }
            )
            entry = MealPlanEntry(
                date=date, recipe_id=recipe_id, title=title,
                entry_type=entry_type, whole_week=whole_week,
            )
            problem = entry_problem(entry)
            if problem:
                raise ValueError(problem)
            return summarize_entry(mealie.create_mealplan(**entry.model_dump()))
        except Exception as e:
            error_msg = f"Error creating mealplan entry: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    def create_mealplan_bulk(
        entries: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create multiple meal plan entries in bulk.

        Every entry is checked before any is created, so a mistake in one creates
        nothing. If Mealie then fails partway, the error says which entries were
        created (with their ids) and which were not, so retry only the rest.

        Args:
            entries: List of mealplan entries, each containing:
                - date (str): Date in ISO format (YYYY-MM-DD)
                - recipe_id (str, optional): UUID of the recipe
                - title (str, optional): Title for the entry
                - entry_type (str, required): Type of entry (breakfast, lunch, dinner,
                  side, snack, drink, dessert)
                - whole_week (bool, optional): Plan it for the whole week containing date

        Returns:
            Dict[str, Any]: created — the entries in the order given, each with its id
                (use it with update_mealplan and delete_mealplan), date, endDate (week
                entries only), entryType, title, text (its note, if any) and
                recipeId/recipeName/recipeSlug
        """
        logger.info({"message": "Creating bulk mealplan entries", "entries_count": len(entries)})
        if not entries:
            raise ToolError("Error creating bulk mealplan entries: entries cannot be empty")

        def describe(index: int, entry: Any) -> str:
            day = entry.get("date") if isinstance(entry, dict) else None
            return f"entry {index + 1}" + (f" ({day})" if day else "")

        parsed: List[MealPlanEntry] = []
        problems: List[str] = []
        for index, raw in enumerate(entries):
            try:
                entry = MealPlanEntry.model_validate(raw)
                problem = entry_problem(entry)
            except ValidationError as e:
                entry, problem = None, "; ".join(field_error(err) for err in e.errors())
            if problem:
                problems.append(f"{describe(index, raw)}: {problem}")
            else:
                parsed.append(entry)
        if problems:
            error_msg = "Error creating bulk mealplan entries: nothing was created. " + "; ".join(problems)
            logger.error({"message": error_msg})
            raise ToolError(error_msg)

        created: List[Dict[str, Any]] = []
        for index, entry in enumerate(parsed):
            try:
                created.append(summarize_entry(mealie.create_mealplan(**entry.model_dump())))
            except Exception as e:
                done = (
                    f"Created {len(created)} of {len(parsed)} entries"
                    + (f" (ids {', '.join(str(c['id']) for c in created)})" if created else "")
                )
                remaining = len(parsed) - index - 1
                rest = (
                    "" if not remaining
                    else f"; entry {index + 2} was not attempted" if remaining == 1
                    else f"; entries {index + 2}-{len(parsed)} were not attempted"
                )
                error_msg = (
                    f"Error creating bulk mealplan entries: {done}; "
                    f"{describe(index, entries[index])} failed: {e}{rest}. "
                    "Retry only the entries that were not created."
                )
                logger.error({"message": error_msg})
                logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
                raise ToolError(error_msg)
        return {"created": created}

    @mcp.tool()
    def update_mealplan(
        entry_id: Union[int, str],
        date: str,
        entry_type: str,
        recipe_id: Optional[str] = None,
        title: Optional[str] = None,
        whole_week: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update an existing meal plan entry's date, type, or recipe assignment.

        Args:
            entry_id: The numeric id of the meal plan entry, from get_all_mealplans or
                create_mealplan
            date: New date for the entry (YYYY-MM-DD); for a week entry, any day in
                the target week
            entry_type: Type of entry (breakfast, lunch, dinner, side, snack, drink,
                dessert)
            recipe_id: UUID of the recipe (optional)
            title: Title for non-recipe entries (optional)
            whole_week: True makes it a whole-week entry, False a single-day entry;
                omit to keep the entry's current kind

        Returns:
            Dict[str, Any]: The updated entry: id, date, endDate (week entries only),
                entryType, title, text (its note, if any) and
                recipeId/recipeName/recipeSlug
        """
        try:
            logger.info({"message": "Updating mealplan entry", "entry_id": entry_id})
            return summarize_entry(mealie.update_mealplan(
                entry_id=entry_id,
                date=date,
                entry_type=entry_type,
                recipe_id=recipe_id,
                title=title,
                whole_week=whole_week,
            ))
        except Exception as e:
            error_msg = f"Error updating mealplan entry '{entry_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def delete_mealplan(entry_id: Union[int, str]) -> Dict[str, Any]:
        """Delete a meal plan entry.

        Args:
            entry_id: The numeric id of the meal plan entry, from get_all_mealplans or
                create_mealplan

        Returns:
            Dict[str, Any]: deleted: the entry as it was (id, date, endDate for week
                entries, entryType, title, text (its note, if any) and
                recipeId/recipeName/recipeSlug)
        """
        try:
            logger.info({"message": "Deleting mealplan entry", "entry_id": entry_id})
            # Mealie's delete reply has no recipe name, so read the entry first
            entry = mealie.get_mealplan(entry_id)
            mealie.delete_mealplan(entry_id=entry_id)
            return {"deleted": [summarize_entry(entry)]}
        except Exception as e:
            error_msg = f"Error deleting mealplan entry '{entry_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_todays_mealplan() -> List[Dict[str, Any]]:
        """Get the mealplan entries for today.

        Whole-week entries are not included (they aren't planned for a specific day);
        use get_all_mealplans with today's date to also see this week's week entries.

        Returns:
            List[Dict[str, Any]]: Today's entries: id, date, entryType, title, text (its
                note, if any), and recipeId / recipeName / recipeSlug for a recipe entry
        """
        try:
            logger.info({"message": "Fetching today's mealplan"})
            return [summarize_entry(e) for e in mealie.get_todays_mealplan()]
        except Exception as e:
            error_msg = f"Error fetching today's mealplan: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)
