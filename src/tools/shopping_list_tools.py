import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher
from trim import trim_item_changes, trim_shopping_item, trim_shopping_list

logger = logging.getLogger("mealie-mcp")


def register_shopping_list_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all shopping list-related tools with the MCP server."""

    def delete_items(item_ids: List[str]) -> Dict[str, Any]:
        """Delete items after checking every id exists, and return what was deleted.

        Mealie reports success for an id that doesn't exist, so a wrong id would read
        as deleted while the intended item stays on the list. One read of all items
        (every list) checks them first; an unknown id deletes nothing.
        """
        ids = list(dict.fromkeys(item_ids))
        if not ids:
            raise ValueError("Item IDs list cannot be empty")
        existing = {
            item["id"]: item
            for item in mealie.get_shopping_list_items(per_page=-1).get("items", [])
        }
        unknown = [item_id for item_id in ids if item_id not in existing]
        if unknown:
            raise ValueError(
                "No shopping list item with id " + ", ".join(unknown)
                + ". Nothing was deleted. Read the list again (get_shopping_list) for current ids."
            )
        if len(ids) == 1:
            mealie.delete_shopping_list_item(ids[0])
        else:
            mealie.delete_shopping_list_items_bulk(ids)
        return {"deleted": [trim_shopping_item(existing[item_id], with_list_id=True) for item_id in ids]}

    # Shopping List Operations

    @mcp.tool()
    def get_shopping_lists(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get all shopping lists for the current household with pagination.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Pagination fields and items: each list's id, name,
                labelOrder (its section names in order) and recipeReferences. Items
                aren't included here; use get_shopping_list for a list's items.
        """
        try:
            logger.info({"message": "Fetching shopping lists", "page": page, "per_page": per_page})
            result = mealie.get_shopping_lists(page=page, per_page=per_page)
            if isinstance(result, dict) and isinstance(result.get("items"), list):
                result = {**result, "items": [trim_shopping_list(i) for i in result["items"]]}
            return result
        except Exception as e:
            error_msg = f"Error fetching shopping lists: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_shopping_list(name: str) -> Dict[str, Any]:
        """Create a new shopping list.

        Args:
            name: Name of the shopping list

        Returns:
            Dict[str, Any]: The created shopping list details
        """
        try:
            logger.info({"message": "Creating shopping list", "name": name})
            return trim_shopping_list(mealie.create_shopping_list(name))
        except Exception as e:
            error_msg = f"Error creating shopping list '{name}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_shopping_list(list_id: str) -> Dict[str, Any]:
        """Get a specific shopping list by ID.

        Args:
            list_id: The UUID of the shopping list

        Returns:
            Dict[str, Any]: id, name, labelOrder (section names in the list's order),
                recipeReferences (each recipe on the list: recipeId, name, slug,
                recipeQuantity) and listItems. Each item: id, display (the line as
                text), checked, quantity, unit, food, label (its store section), note,
                and recipeIds (the recipes it came from). Use get_recipe_detailed for a
                recipe's full details.
        """
        try:
            logger.info({"message": "Fetching shopping list", "list_id": list_id})
            return trim_shopping_list(mealie.get_shopping_list(list_id))
        except Exception as e:
            error_msg = f"Error fetching shopping list '{list_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def update_shopping_list(list_id: str, name: str) -> Dict[str, Any]:
        """Rename an existing shopping list.

        Args:
            list_id: The UUID of the shopping list to update
            name: New name for the shopping list

        Returns:
            Dict[str, Any]: The updated shopping list
        """
        try:
            logger.info({"message": "Updating shopping list", "list_id": list_id})
            return trim_shopping_list(mealie.update_shopping_list(list_id, {"name": name}))
        except Exception as e:
            error_msg = f"Error updating shopping list '{list_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def update_shopping_list_label_settings(
        list_id: str,
        labels: List[str],
    ) -> Dict[str, Any]:
        """Reorder a shopping list's sections to match a store's layout. Each section
        is a label (the store section a food is filed under), and every list keeps
        its own order.

        Call get_labels first and use the label names exactly as returned: names are
        whatever this Mealie defines, so never guess or invent one. Matching ignores
        case. If any name is unknown, nothing is changed and the error lists the
        list's real label names.

        Example: labels=["<first label name from get_labels>", "<next label name>", ...]

        Args:
            list_id: The UUID of the shopping list
            labels: Label names in the order the store is walked. Labels left out
                keep their current relative order after the named ones.

        Returns:
            Dict[str, Any]: The list's id and name, and labelOrder — every label
                name in the resulting order
        """
        try:
            logger.info({"message": "Updating shopping list label order", "list_id": list_id, "labels": labels})
            if not labels:
                raise ValueError("Give at least one label name, in store order (see get_labels)")

            current = sorted(
                mealie.get_shopping_list(list_id).get("labelSettings") or [],
                key=lambda setting: setting.get("position", 0),
            )
            lookup: Dict[str, Dict[str, Any]] = {}
            for setting in current:
                name = (setting.get("label") or {}).get("name")
                if name:
                    lookup[name.strip().lower()] = setting
                # A label id is accepted too, for a caller that already has one
                lookup[str(setting.get("labelId", "")).lower()] = setting

            unknown = [name for name in labels if str(name).strip().lower() not in lookup]
            if unknown:
                valid = sorted(
                    (setting.get("label") or {}).get("name", "") for setting in current
                )
                raise ValueError(
                    "Unknown label "
                    + ", ".join(f'"{name}"' for name in unknown)
                    + ". Nothing was changed. This list's labels are: "
                    + ", ".join(valid)
                )

            ordered: List[Dict[str, Any]] = []
            for name in labels:
                setting = lookup[str(name).strip().lower()]
                if setting not in ordered:
                    ordered.append(setting)
            ordered += [setting for setting in current if setting not in ordered]

            payload = [
                {
                    "id": setting["id"],
                    "shoppingListId": list_id,
                    "labelId": setting["labelId"],
                    "position": position,
                }
                for position, setting in enumerate(ordered)
            ]
            updated = mealie.update_shopping_list_label_settings(list_id, payload)
            return {
                "id": updated.get("id", list_id),
                "name": updated.get("name"),
                "labelOrder": [
                    (setting.get("label") or {}).get("name")
                    for setting in sorted(
                        updated.get("labelSettings") or [],
                        key=lambda setting: setting.get("position", 0),
                    )
                ],
            }
        except Exception as e:
            error_msg = f"Error updating label order for list '{list_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def add_recipes_to_shopping_list_bulk(
        list_id: str,
        recipes: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Add multiple recipes' ingredients to a shopping list in one request.

        Each entry must include a recipeId (recipe UUID). Optionally include
        recipeIncrementQuantity to scale ingredients.
        Example: [{"recipeId": "recipe-uuid", "recipeIncrementQuantity": 1.0}]

        Args:
            list_id: The UUID of the shopping list
            recipes: List of recipe objects with recipeId and optional quantity multiplier

        Returns:
            Dict[str, Any]: The updated shopping list
        """
        try:
            logger.info({
                "message": "Bulk adding recipes to shopping list",
                "list_id": list_id,
                "count": len(recipes),
            })
            return trim_shopping_list(mealie.add_recipes_to_shopping_list_bulk(list_id, recipes))
        except Exception as e:
            error_msg = f"Error bulk adding recipes to shopping list '{list_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def delete_shopping_list(list_id: str) -> Dict[str, Any]:
        """Delete a specific shopping list.

        Args:
            list_id: The UUID of the shopping list to delete

        Returns:
            Dict[str, Any]: deleted: the list's id, name and itemCount (its items are
                deleted with it)
        """
        try:
            logger.info({"message": "Deleting shopping list", "list_id": list_id})
            deleted = mealie.delete_shopping_list(list_id)
            return {"deleted": [{
                "id": deleted.get("id", list_id),
                "name": deleted.get("name"),
                "itemCount": len(deleted.get("listItems") or []),
            }]}
        except Exception as e:
            error_msg = f"Error deleting shopping list '{list_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def add_recipe_to_shopping_list(
        list_id: str,
        recipe_id: str,
        recipe_increment_quantity: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Add a recipe's ingredients to a shopping list.

        Args:
            list_id: The UUID of the shopping list
            recipe_id: The UUID of the recipe to add
            recipe_increment_quantity: Multiplier for recipe quantities (e.g., 2.0 for double)

        Returns:
            Dict[str, Any]: The updated shopping list
        """
        try:
            logger.info({
                "message": "Adding recipe to shopping list",
                "list_id": list_id,
                "recipe_id": recipe_id,
            })
            return trim_shopping_list(mealie.add_recipe_to_shopping_list(
                list_id, recipe_id, recipe_increment_quantity
            ))
        except Exception as e:
            error_msg = f"Error adding recipe to shopping list: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def remove_recipe_from_shopping_list(
        list_id: str,
        recipe_id: str,
    ) -> Dict[str, Any]:
        """Remove a recipe's ingredients from a shopping list.

        Args:
            list_id: The UUID of the shopping list
            recipe_id: The UUID of the recipe to remove

        Returns:
            Dict[str, Any]: The updated shopping list
        """
        try:
            logger.info({
                "message": "Removing recipe from shopping list",
                "list_id": list_id,
                "recipe_id": recipe_id,
            })
            return trim_shopping_list(mealie.remove_recipe_from_shopping_list(list_id, recipe_id))
        except Exception as e:
            error_msg = f"Error removing recipe from shopping list: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    # Shopping List Item Operations

    @mcp.tool()
    def get_shopping_list_items(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get all shopping list items with pagination and search.

        Args:
            page: Page number to retrieve
            per_page: Number of items per page
            search: Search term to filter items

        Returns:
            Dict[str, Any]: Pagination fields and items, across all lists: each item's
                id, shoppingListId, display, checked, quantity, unit, food, label,
                note and recipeIds
        """
        try:
            logger.info({
                "message": "Fetching shopping list items",
                "page": page,
                "per_page": per_page,
                "search": search,
            })
            result = mealie.get_shopping_list_items(page=page, per_page=per_page, search=search)
            if isinstance(result, dict) and isinstance(result.get("items"), list):
                result = {**result, "items": [trim_shopping_item(i, with_list_id=True) for i in result["items"]]}
            return result
        except Exception as e:
            error_msg = f"Error fetching shopping list items: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_shopping_list_item(item_id: str) -> Dict[str, Any]:
        """Get a specific shopping list item by ID.

        Args:
            item_id: The UUID of the shopping list item

        Returns:
            Dict[str, Any]: The item's id, shoppingListId, display, checked, quantity,
                unit, food, label, note and recipeIds
        """
        try:
            logger.info({"message": "Fetching shopping list item", "item_id": item_id})
            return trim_shopping_item(mealie.get_shopping_list_item(item_id), with_list_id=True)
        except Exception as e:
            error_msg = f"Error fetching shopping list item '{item_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_shopping_list_item(
        shopping_list_id: str,
        note: str,
        quantity: Optional[float] = None,
        unit_id: Optional[str] = None,
        food_id: Optional[str] = None,
        label_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a new item in a shopping list.

        Args:
            shopping_list_id: UUID of the shopping list
            note: Item description (e.g., "2 lbs chicken breast")
            quantity: Item quantity
            unit_id: UUID of the unit (optional)
            food_id: UUID of the food (optional)
            label_id: UUID of the label (optional)

        Returns:
            Dict[str, Any]: What happened: created, updated and deleted. Mealie adds to a matching line
                instead of making a second one (same food and unit, or the same note
                text), so an item can come back under updated, e.g. "3 cups onion"
                after adding 1 cup to 2. created and updated hold the items (id,
                shoppingListId, display, checked, quantity, unit, food, label, note,
                recipeIds); deleted holds the ids of lines merged into another. Empty
                parts are left out.
        """
        try:
            logger.info({
                "message": "Creating shopping list item",
                "shopping_list_id": shopping_list_id,
                "note": note,
            })
            return trim_item_changes(mealie.create_shopping_list_item(
                shopping_list_id, note, quantity, unit_id, food_id, label_id
            ))
        except Exception as e:
            error_msg = f"Error creating shopping list item: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_shopping_list_items_bulk(
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Create multiple shopping list items at once.

        Args:
            items: List of item dictionaries, each containing:
                - shoppingListId (str): UUID of the shopping list
                - note (str): Item description
                - quantity (float, optional): Item quantity
                - unit_id (str, optional): UUID of the unit
                - food_id (str, optional): UUID of the food

        Returns:
            Dict[str, Any]: What happened: created, updated and deleted. Mealie adds to a matching line
                instead of making a second one (same food and unit, or the same note
                text), so an item can come back under updated, e.g. "3 cups onion"
                after adding 1 cup to 2. created and updated hold the items (id,
                shoppingListId, display, checked, quantity, unit, food, label, note,
                recipeIds); deleted holds the ids of lines merged into another. Empty
                parts are left out. Duplicates within the batch
                are combined into one item.
        """
        try:
            logger.info({"message": "Creating bulk shopping list items", "count": len(items)})
            return trim_item_changes(mealie.create_shopping_list_items_bulk(items))
        except Exception as e:
            error_msg = f"Error creating bulk shopping list items: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def update_shopping_list_item(
        item_id: str,
        note: Optional[str] = None,
        quantity: Optional[float] = None,
        checked: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Update a shopping list item. Use this to check/uncheck items or modify their details.

        Args:
            item_id: The UUID of the shopping list item to update
            note: Updated item description
            quantity: Updated quantity
            checked: Whether the item is checked off

        Returns:
            Dict[str, Any]: What happened: created, updated and deleted. Mealie adds to a matching line
                instead of making a second one (same food and unit, or the same note
                text), so an item can come back under updated, e.g. "3 cups onion"
                after adding 1 cup to 2. created and updated hold the items (id,
                shoppingListId, display, checked, quantity, unit, food, label, note,
                recipeIds); deleted holds the ids of lines merged into another. Empty
                parts are left out. Unchecking an item, or
                changing it to match another line, can merge the two: the kept line
                is under updated and the other's id under deleted.
        """
        try:
            logger.info({"message": "Updating shopping list item", "item_id": item_id})

            item_data = {}
            if note is not None:
                item_data["note"] = note
            if quantity is not None:
                item_data["quantity"] = quantity
            if checked is not None:
                item_data["checked"] = checked

            if not item_data:
                raise ValueError("At least one field must be provided to update")

            return trim_item_changes(mealie.update_shopping_list_item(item_id, item_data))
        except Exception as e:
            error_msg = f"Error updating shopping list item '{item_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def delete_shopping_list_item(item_id: str) -> Dict[str, Any]:
        """Delete a specific shopping list item.

        Args:
            item_id: The UUID of the shopping list item to delete

        Returns:
            Dict[str, Any]: deleted: the item as it was (id, shoppingListId, display,
                checked, ...). An unknown id is an error and nothing is deleted.
        """
        try:
            logger.info({"message": "Deleting shopping list item", "item_id": item_id})
            return delete_items([item_id])
        except Exception as e:
            error_msg = f"Error deleting shopping list item '{item_id}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def update_shopping_list_items_bulk(
        items: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Update multiple shopping list items at once, e.g. check off several items.

        Each item needs its id plus only the fields to change (note, quantity,
        checked, etc.); every other field keeps its current value.

        Args:
            items: List of item dictionaries, each with id and the fields to update

        Returns:
            Dict[str, Any]: What happened: created, updated and deleted. Mealie adds to a matching line
                instead of making a second one (same food and unit, or the same note
                text), so an item can come back under updated, e.g. "3 cups onion"
                after adding 1 cup to 2. created and updated hold the items (id,
                shoppingListId, display, checked, quantity, unit, food, label, note,
                recipeIds); deleted holds the ids of lines merged into another. Empty
                parts are left out. Unchecking items, or
                changing them to match other lines, can merge lines.
        """
        try:
            logger.info({"message": "Updating bulk shopping list items", "count": len(items)})
            return trim_item_changes(mealie.update_shopping_list_items_bulk(items))
        except Exception as e:
            error_msg = f"Error updating bulk shopping list items: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def delete_shopping_list_items_bulk(
        item_ids: List[str],
    ) -> Dict[str, Any]:
        """Delete multiple shopping list items at once.

        Args:
            item_ids: List of shopping list item UUIDs to delete

        Returns:
            Dict[str, Any]: deleted: each item as it was (id, shoppingListId, display,
                checked, ...). Every id is checked first: if any is unknown, nothing is
                deleted and the error names it. Ids may come from different lists.
        """
        try:
            logger.info({"message": "Deleting bulk shopping list items", "count": len(item_ids)})
            return delete_items(item_ids)
        except Exception as e:
            error_msg = f"Error deleting bulk shopping list items: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)
