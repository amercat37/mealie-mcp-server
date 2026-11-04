"""Trim Mealie's responses to what an assistant needs.

Mealie nests full copies of organizers (tags, categories, tools), foods, units and
labels inside recipes and list items, each with internal ids, timestamps and a
`recipeCount` that is always 0 on these nested copies. Most of a response is that
repetition, and it can be too big for an assistant to read whole.
"""

from typing import Any, Dict, List, Optional

from recipe_times import TIME_FIELDS

# Recipe fields dropped from get_recipe_detailed: internal ids, duplicate timestamps,
# image key, display settings, and data other tools return (comments) or that is
# always empty (cookTime: Mealie keeps the cook time in performTime).
DETAIL_DROP = (
    "userId", "groupId", "householdId", "createdAt", "updatedAt", "image",
    "cookTime", "extras", "settings", "comments", "assets",
)

# A recipe in get_recipes, in this order
SUMMARY_FIELDS = (
    "id", "name", "slug", "description", "tags", "recipeCategory", "tools",
    *(name for field in TIME_FIELDS for name in (field, f"{field}Seconds")),
    "recipeServings", "recipeYieldQuantity", "recipeYield", "rating",
    "dateAdded", "dateUpdated",
)

ORGANIZERS = ("tags", "recipeCategory", "tools")


def present(value: Any) -> bool:
    """Whether a field is worth showing: not None, empty text or an empty list/dict."""
    return value is not None and value != "" and value != [] and value != {}


def slugs(organizers: Optional[List[Any]]) -> List[str]:
    """Tags, categories or tools as their slugs (the values the filters take)."""
    return [o["slug"] if isinstance(o, dict) else o for o in organizers or []
            if not isinstance(o, dict) or o.get("slug")]


def name_of(obj: Any) -> Optional[str]:
    """The name of a nested food, unit or label object."""
    return obj.get("name") if isinstance(obj, dict) else obj


def trim_ingredient(ingredient: Dict[str, Any]) -> Dict[str, Any]:
    """A recipe ingredient line with the food, unit and label as names.

    referenceId is kept: instruction steps link to ingredients by it.
    """
    out: Dict[str, Any] = {}
    for field in ("title", "quantity", "note", "display", "referenceId"):
        if present(ingredient.get(field)) and ingredient.get(field) != 0:
            out[field] = ingredient[field]
    if ingredient.get("unit"):
        out["unit"] = name_of(ingredient["unit"])
    food = ingredient.get("food")
    if food:
        out["food"] = name_of(food)
        if isinstance(food, dict) and food.get("label"):
            out["label"] = name_of(food["label"])
    if ingredient.get("referencedRecipe"):
        ref = ingredient["referencedRecipe"]
        out["referencedRecipe"] = ref.get("slug") if isinstance(ref, dict) else ref
    if ingredient.get("substitutions"):
        out["substitutions"] = [trim_ingredient(s) for s in ingredient["substitutions"]]
    return out


def trim_recipe_summary(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """A recipe in get_recipes: what's needed to browse and choose.

    Expects readable times already filled in (add_readable_times).
    """
    out: Dict[str, Any] = {}
    for field in SUMMARY_FIELDS:
        value = recipe.get(field)
        if field in ORGANIZERS:
            out[field] = slugs(value)
        elif present(value) and value != 0:
            out[field] = value
    return out


def trim_recipe_detail(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """A whole recipe for get_recipe_detailed, without the nested copies.

    Fields not named here pass through, so a field Mealie adds later still shows.
    """
    out: Dict[str, Any] = {}
    for field, value in recipe.items():
        if field in DETAIL_DROP:
            continue
        if field in ORGANIZERS:
            out[field] = slugs(value)
        elif field == "recipeIngredient":
            out[field] = [trim_ingredient(i) for i in value or []]
        elif field == "recipeInstructions":
            out[field] = [{k: v for k, v in step.items() if present(v)} for step in value or []]
        else:
            out[field] = value
    return out


def trim_recipe_concise(recipe: Dict[str, Any]) -> Dict[str, Any]:
    """A recipe for get_recipe_concise: amounts and ingredients for planning or shopping."""
    out: Dict[str, Any] = {}
    for field in ("name", "slug", "recipeServings", "recipeYieldQuantity", "recipeYield",
                  "totalTime", "rating", "lastMade"):
        if present(recipe.get(field)) and recipe.get(field) != 0:
            out[field] = recipe[field]
    out["recipeIngredient"] = [trim_ingredient(i) for i in recipe.get("recipeIngredient") or []]
    return out


def trim_shopping_item(item: Dict[str, Any], with_list_id: bool = False) -> Dict[str, Any]:
    """A shopping list item: what it is, whether it's checked, and its store section.

    recipeIds lists the recipes the item came from (their names are in the list's
    recipeReferences). with_list_id adds shoppingListId, for items read outside a list.
    """
    out: Dict[str, Any] = {"id": item.get("id")}
    if with_list_id:
        out["shoppingListId"] = item.get("shoppingListId")
    out["display"] = item.get("display")
    out["checked"] = bool(item.get("checked"))
    if item.get("quantity"):
        out["quantity"] = item["quantity"]
    for field in ("unit", "food", "label"):
        if item.get(field):
            out[field] = name_of(item[field])
    if present(item.get("note")):
        out["note"] = item["note"]
    if item.get("referencedRecipe"):
        ref = item["referencedRecipe"]
        out["referencedRecipe"] = ref.get("slug") if isinstance(ref, dict) else ref
    recipe_ids = [ref.get("recipeId") for ref in item.get("recipeReferences") or [] if ref.get("recipeId")]
    if recipe_ids:
        out["recipeIds"] = recipe_ids
    return out


def trim_shopping_list(shopping_list: Any) -> Any:
    """A shopping list: id, name, labelOrder (section names in the list's order),
    recipeReferences (recipeId, name, slug, recipeQuantity) and trimmed listItems.

    Mealie embeds a full recipe summary in every recipe reference and full food, unit
    and label objects in every item. A part Mealie didn't send (list summaries have no
    listItems) is left out. Only tool output is trimmed — never data sent to Mealie.
    """
    if not isinstance(shopping_list, dict):
        return shopping_list
    out: Dict[str, Any] = {"id": shopping_list.get("id"), "name": shopping_list.get("name")}
    if isinstance(shopping_list.get("labelSettings"), list):
        out["labelOrder"] = [
            name_of(setting.get("label"))
            for setting in sorted(shopping_list["labelSettings"], key=lambda s: s.get("position", 0))
        ]
    if isinstance(shopping_list.get("recipeReferences"), list):
        out["recipeReferences"] = [
            {
                "recipeId": ref.get("recipeId"),
                "name": (ref.get("recipe") or {}).get("name"),
                "slug": (ref.get("recipe") or {}).get("slug"),
                "recipeQuantity": ref.get("recipeQuantity"),
            }
            for ref in shopping_list["recipeReferences"]
        ]
    if isinstance(shopping_list.get("listItems"), list):
        out["listItems"] = [trim_shopping_item(i) for i in shopping_list["listItems"]]
    return out
