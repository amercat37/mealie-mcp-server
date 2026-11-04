import logging
import traceback
import uuid
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher
from models.recipe import RecipeCreate
from recipe_times import add_readable_times
from trim import trim_recipe_concise, trim_recipe_detail, trim_recipe_summary

logger = logging.getLogger("mealie-mcp")


def register_recipe_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all recipe-related tools with the MCP server."""

    def add_last_made(slug: str, recipe: Dict[str, Any]) -> Dict[str, Any]:
        """Set recipe["lastMade"] from the household's recipe data, where Mealie v3.29+
        keeps it. A failed lookup is logged and skipped rather than failing the read."""
        try:
            recipe["lastMade"] = mealie.get_household_recipe(slug).get("lastMade")
        except Exception as e:
            logger.warning({"message": "Could not fetch lastMade", "slug": slug, "error": str(e)})
        return recipe

    @mcp.tool()
    def get_recipes(
        search: Optional[str] = None,
        page: Optional[int] = None,
        per_page: Optional[int] = None,
        categories: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        require_all_tags: Optional[bool] = None,
        require_all_categories: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """Provides a paginated list of recipes with optional filtering.

        IMPORTANT: When filtering by tags or categories, you MUST use slugs or UUIDs, NOT display names!
        - ✅ Correct: tags=["quick-meals", "vegetarian"]
        - ❌ Wrong: tags=["Quick Meals", "Vegetarian"]

        Use get_tags() or get_categories() first to find the correct slugs.

        Args:
            search: Filters recipes by name or description.
            page: Page number for pagination.
            per_page: Number of items per page.
            categories: Filter by category SLUGS (e.g., ["breakfast", "dinner"]).
            tags: Filter by tag SLUGS or UUIDs (e.g., ["quick", "healthy"]).
            require_all_tags: If True, recipe must have ALL specified tags (AND). Default False (OR).
            require_all_categories: If True, recipe must have ALL specified categories (AND).

        Returns:
            Dict[str, Any]: Pagination fields and items, one short entry per recipe: id
                (use it as recipe_id in meal plans and shopping lists), name, slug,
                description, tags / recipeCategory / tools as slugs, prepTime/performTime/
                totalTime as readable text ("1 hour 30 minutes") plus *TimeSeconds as
                numbers for comparisons, recipeServings, recipeYieldQuantity + recipeYield,
                rating (if set), dateAdded, dateUpdated. Ingredients and instructions are
                not included: use get_recipe_concise (ingredients) or get_recipe_detailed
                (everything) for a chosen recipe.
        """
        try:
            logger.info(
                {
                    "message": "Fetching recipes",
                    "search": search,
                    "page": page,
                    "per_page": per_page,
                    "categories": categories,
                    "tags": tags,
                    "require_all_tags": require_all_tags,
                    "require_all_categories": require_all_categories,
                }
            )
            result = mealie.get_recipes(
                search=search,
                page=page,
                per_page=per_page,
                categories=categories,
                tags=tags,
                require_all_tags=require_all_tags,
                require_all_categories=require_all_categories,
            )
            result["items"] = [
                trim_recipe_summary(add_readable_times(item)) for item in result.get("items", [])
            ]
            return result
        except Exception as e:
            error_msg = f"Error fetching recipes: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_detailed(slug: str) -> Dict[str, Any]:
        """Retrieve a specific recipe by its slug identifier. Use this to get full recipe
        details for tasks like updating or displaying the recipe.

        Args:
            slug: The unique text identifier for the recipe, typically found in recipe URLs
                or from get_recipes results.

        Returns:
            Dict[str, Any]: The whole recipe: ingredients, instructions, nutrition, notes,
                description, servings and yield, rating, orgURL (where it was imported
                from), dates, and tags / recipeCategory / tools as slugs. Each ingredient
                gives food, unit and label (store section) as names, plus quantity, note,
                display (the full line as text) and referenceId (instruction steps link to
                ingredients by it). prepTime/performTime/totalTime are readable text; the
                *TimeSeconds fields hold the same times as numbers. lastMade is the
                household's last made date (null if never made).
        """
        try:
            logger.info({"message": "Fetching recipe", "slug": slug})
            recipe_json = add_readable_times(mealie.get_recipe(slug))
            return trim_recipe_detail(add_last_made(slug, recipe_json))
        except Exception as e:
            error_msg = f"Error fetching recipe with slug '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_concise(slug: str) -> Dict[str, Any]:
        """Retrieve a concise version of a specific recipe by its slug identifier. Use this when you only
        need a summary of the recipe, such as for when mealplaning.

        Args:
            slug: The unique text identifier for the recipe, typically found in recipe URLs
                or from get_recipes results.

        Returns:
            Dict[str, Any]: name, slug, recipeServings, recipeYieldQuantity + recipeYield,
                totalTime, rating and lastMade (when set), and recipeIngredient: each
                ingredient's food, unit and label (store section) as names, plus quantity,
                note and display (the full line as text).
        """
        try:
            logger.info({"message": "Fetching recipe", "slug": slug})
            recipe_json = add_last_made(slug, add_readable_times(mealie.get_recipe(slug)))
            return trim_recipe_concise(recipe_json)
        except Exception as e:
            error_msg = f"Error fetching recipe with slug '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug(
                {"message": "Error traceback", "traceback": traceback.format_exc()}
            )
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_comments(slug: str) -> List[Dict[str, Any]]:
        """Get all comments on a recipe.

        Args:
            slug: The unique text identifier for the recipe

        Returns:
            List[Dict[str, Any]]: List of comments with text, author, and timestamps
        """
        try:
            logger.info({"message": "Fetching recipe comments", "slug": slug})
            return mealie.get_recipe_comments(slug)
        except Exception as e:
            error_msg = f"Error fetching comments for recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_recipe_comment(slug: str, text: str) -> Dict[str, Any]:
        """Post a comment on a recipe. Use this to record cooking notes such as
        substitutions made, timing adjustments, or how the dish turned out.

        Args:
            slug: The unique text identifier for the recipe
            text: The comment text

        Returns:
            Dict[str, Any]: The created comment
        """
        try:
            logger.info({"message": "Creating recipe comment", "slug": slug})
            return mealie.create_recipe_comment(slug, text)
        except Exception as e:
            error_msg = f"Error creating comment for recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_timeline(
        page: Optional[int] = None,
        per_page: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get a chronological activity feed across all recipes. Use this to answer
        questions like 'what did I cook last Wednesday?' or 'what have I been making lately?'

        Args:
            page: Page number to retrieve
            per_page: Number of items per page

        Returns:
            Dict[str, Any]: Timeline events with recipe names and timestamps
        """
        try:
            logger.info({"message": "Fetching recipe timeline"})
            return mealie.get_recipe_timeline(page=page, per_page=per_page)
        except Exception as e:
            error_msg = f"Error fetching recipe timeline: {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_share_tokens(slug: str) -> List[Dict[str, Any]]:
        """List existing public share links for a recipe.

        Args:
            slug: The unique text identifier for the recipe

        Returns:
            List[Dict[str, Any]]: List of share tokens with URLs and expiry info
        """
        try:
            logger.info({"message": "Fetching recipe share tokens", "slug": slug})
            return mealie.get_recipe_share_tokens(slug)
        except Exception as e:
            error_msg = f"Error fetching share tokens for recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_recipe_share_token(slug: str) -> Dict[str, Any]:
        """Create a public share link for a recipe. Use this to share a recipe
        with someone outside Mealie (e.g., text it to a family member).

        Args:
            slug: The unique text identifier for the recipe

        Returns:
            Dict[str, Any]: The new share token including the shareable URL
        """
        try:
            logger.info({"message": "Creating recipe share token", "slug": slug})
            return mealie.create_recipe_share_token(slug)
        except Exception as e:
            error_msg = f"Error creating share token for recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def get_recipe_exports(slug: str) -> Dict[str, Any]:
        """Get available export formats and download links for a recipe,
        including a PDF download link.

        Args:
            slug: The unique text identifier for the recipe

        Returns:
            Dict[str, Any]: Available export formats and their download URLs
        """
        try:
            logger.info({"message": "Fetching recipe exports", "slug": slug})
            return mealie.get_recipe_exports(slug)
        except Exception as e:
            error_msg = f"Error fetching exports for recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def create_recipe(recipe: RecipeCreate) -> Dict[str, Any]:
        """Create a new recipe in Mealie.

        Before calling this tool:
        1. Fetch 2-3 existing similar recipes with get_recipe_detailed to observe the
           category/tag/tool patterns used — follow those patterns, don't invent new ones.
        2. For every ingredient food, search the catalog with get_foods first. Pick the
           existing food that best covers the ingredient (e.g. "black pepper" covers
           "pepper"). Only use a name that isn't in the catalog if the food is truly
           absent — the tool will create it automatically.
        3. For every ingredient unit, call get_units first and pick the best match
           (e.g. "c" or "cup" → use the existing "cup" unit) so the unit is stored
           structurally. A unit with no catalog match is not dropped — it is appended
           to the ingredient's note so the text is preserved — but prefer matching an
           existing unit, since a note-only unit does not participate in scaling.
        4. Always include "my-recipes" in tags (default). Use "the-autoimmune-solution"
           instead if the recipe belongs to that cookbook.
        5. Servings and yield — set only what fits the recipe (Mealie shows them separately):
           recipeServings is the number of people served (e.g. 4) — use it for most dishes.
           recipeYieldQuantity + recipeYield describe a produced amount: recipeYieldQuantity is
           the number (e.g. 12) and recipeYield is the BARE unit only ("cookies", "cups", "loaf"),
           shown together as "12 cookies". Never put a per-serving breakdown or sentence in
           recipeYield. Most people-fed dishes use recipeServings only and leave yield blank; set
           yield only when the output is a countable/measurable thing worth stating; set both only
           when the yield differs from portioning (e.g. yields 12 meatballs but serves 4).
        6. Time: use human-readable strings WITH a unit — e.g. "30 minutes", "1 hour",
           "1 hour 30 minutes". A bare number like "45" is rejected (minutes or hours?).
           Alternatively pass prepTimeSeconds/performTimeSeconds/totalTimeSeconds as numbers
           (e.g. copied from get_recipe_detailed). Times are stored as Mealie's structured
           durations; a non-duration such as "overnight" is kept as text. Omit a time that
           doesn't apply (e.g. no cook time) rather than sending "0 minutes".
        7. Nutrition: always populate every nutrition field (calories, carbohydrateContent,
           cholesterolContent, fatContent, fiberContent, proteinContent, saturatedFatContent,
           sodiumContent, sugarContent, transFatContent, unsaturatedFatContent). Enter
           per-serving values — Mealie stores nutrition statically and never rescales it.
           Estimate from standard sources if exact values are unknown. All values are strings.

        The tool resolves all slug and name references to IDs automatically before saving.
        When nutrition data is provided, showNutrition is enabled automatically.

        Use these EXACT field names (unknown fields are rejected, not ignored):
        recipeCategory, tags, tools, recipeIngredient, recipeInstructions, prepTime,
        performTime (the cook/active time), totalTime, prepTimeSeconds,
        performTimeSeconds, totalTimeSeconds, recipeServings,
        recipeYieldQuantity, recipeYield, orgURL, nutrition, notes. Worked example:

            {
              "name": "Quick Tomato Sauce",
              "recipeCategory": ["sauce"],
              "tags": ["my-recipes"],
              "recipeServings": 4,
              "recipeYieldQuantity": 2, "recipeYield": "cups",
              "prepTime": "10 minutes", "performTime": "20 minutes", "totalTime": "30 minutes",
              "recipeIngredient": [
                {"quantity": 2, "unit": "cup", "food": "tomato", "note": "chopped"}
              ],
              "recipeInstructions": [{"text": "Simmer until thick."}],
              "nutrition": {"calories": "90", "carbohydrateContent": "12"}
            }

        Args:
            recipe: RecipeCreate object with name, description, categories (slugs),
                tags (slugs), tools (slugs), ingredients (food/unit names), instructions,
                timing, servings, yield, source URL, nutrition, and notes.

        Returns:
            Dict[str, Any]: The fully created recipe as returned by Mealie
        """
        try:
            logger.info({"message": "Creating recipe", "name": recipe.name})

            # Step 1: POST to create skeleton, get slug
            slug = mealie.create_recipe(recipe.name)
            if not isinstance(slug, str):
                slug = slug.get("slug", slug)

            # Step 2: Resolve categories, tags, tools → full objects.
            # Match by slug OR name, case-insensitively, so a value the LLM sends as a
            # display name or wrong case ("Sauce" vs "sauce") resolves instead of being
            # silently dropped. Any genuinely-unmatched value is logged, not swallowed.
            def resolve_organizer(
                items: List[str], fetch_fn, kind: str = "organizer"
            ) -> List[Dict[str, Any]]:
                if not items:
                    return []
                all_items = fetch_fn(per_page=200).get("items", [])
                lookup: Dict[str, Any] = {}
                for i in all_items:
                    if i.get("slug"):
                        lookup[str(i["slug"]).lower()] = i
                    if i.get("name"):
                        lookup[str(i["name"]).lower()] = i
                resolved: List[Dict[str, Any]] = []
                for s in items:
                    obj = lookup.get(str(s).lower())
                    if obj is not None:
                        resolved.append(obj)
                    else:
                        logger.info({"message": f"{kind} not matched — dropped", "value": s})
                return resolved

            resolved_categories = resolve_organizer(recipe.recipeCategory, mealie.get_categories, "category")
            resolved_tags = resolve_organizer(recipe.tags, mealie.get_tags, "tag")
            resolved_tools = resolve_organizer(recipe.tools, mealie.get_organizer_tools, "tool")

            # Step 3: Resolve ingredient food names and unit names → full objects
            all_foods = mealie.get_foods(per_page=500).get("items", [])
            food_lookup = {f["name"].lower(): f for f in all_foods if f.get("name")}

            all_units = mealie.get_organizer_units(per_page=200).get("items", [])
            unit_lookup = {u["name"].lower(): u for u in all_units}
            unit_lookup.update({u.get("abbreviation", "").lower(): u for u in all_units if u.get("abbreviation")})

            resolved_ingredients = []
            for ing in recipe.recipeIngredient:
                # Mealie stores an ingredient sent without a referenceId with none,
                # then makes up a new random one on every read. Send one, as Mealie's
                # own editor does, so the id is stored and stays the same.
                resolved: Dict[str, Any] = {"referenceId": str(uuid.uuid4())}
                if ing.title:
                    resolved["title"] = ing.title
                if ing.quantity is not None:
                    resolved["quantity"] = ing.quantity
                if ing.note:
                    resolved["note"] = ing.note
                resolved["disableAmount"] = ing.disableAmount
                if ing.food:
                    food_obj = food_lookup.get(ing.food.lower())
                    if not food_obj:
                        created = mealie.create_food(ing.food)
                        food_lookup[ing.food.lower()] = created
                        food_obj = created
                        logger.info({"message": "Auto-created food", "name": ing.food})
                    resolved["food"] = food_obj
                if ing.unit:
                    unit_obj = unit_lookup.get(ing.unit.lower())
                    if unit_obj:
                        resolved["unit"] = unit_obj
                    else:
                        # Mealie requires a unit id on PATCH, so an unresolvable
                        # unit can't go in the structured unit field. Preserve the
                        # text by appending it to the note rather than dropping it,
                        # and log it so it can be corrected on review.
                        existing_note = resolved.get("note")
                        resolved["note"] = (
                            f"{existing_note}, {ing.unit}" if existing_note else ing.unit
                        )
                        logger.info(
                            {
                                "message": "Unknown unit preserved in note",
                                "unit": ing.unit,
                                "food": ing.food,
                            }
                        )
                resolved_ingredients.append(resolved)

            # Step 4: Build patch payload
            patch_data: Dict[str, Any] = {
                "recipeCategory": resolved_categories,
                "tags": resolved_tags,
                "tools": resolved_tools,
                "recipeIngredient": resolved_ingredients,
                "recipeInstructions": [
                    {"title": i.title or "", "text": i.text, "summary": "", "ingredientReferences": []}
                    for i in recipe.recipeInstructions
                ],
            }
            if recipe.description:
                patch_data["description"] = recipe.description
            patch_data.update(recipe.time_patch())
            if recipe.recipeServings:
                patch_data["recipeServings"] = recipe.recipeServings
            if recipe.recipeYieldQuantity:
                patch_data["recipeYieldQuantity"] = recipe.recipeYieldQuantity
            if recipe.recipeYield:
                patch_data["recipeYield"] = recipe.recipeYield
            if recipe.orgURL:
                patch_data["orgURL"] = recipe.orgURL
            if recipe.nutrition:
                patch_data["nutrition"] = recipe.nutrition.model_dump(exclude_none=True)
                patch_data["settings"] = {"showNutrition": True}
            if recipe.notes:
                patch_data["notes"] = recipe.notes

            # Step 5: PATCH with full data
            return add_readable_times(mealie.patch_recipe(slug, patch_data))
        except Exception as e:
            error_msg = f"Error creating recipe '{recipe.name}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def duplicate_recipe(slug: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Clone an existing recipe under a new name. Use this before making
        significant variations (e.g., a vegetarian version, a scaled-up batch).

        Args:
            slug: The unique text identifier of the recipe to clone
            name: Name for the new copy (defaults to original name with copy indicator)

        Returns:
            Dict[str, Any]: The newly created duplicate recipe
        """
        try:
            logger.info({"message": "Duplicating recipe", "slug": slug, "name": name})
            return add_readable_times(mealie.duplicate_recipe(slug, name=name))
        except Exception as e:
            error_msg = f"Error duplicating recipe '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)

    @mcp.tool()
    def mark_recipe_last_made(slug: str) -> Dict[str, Any]:
        """Mark a recipe as having been made today (updates last made timestamp).

        Args:
            slug: The unique text identifier for the recipe.

        Returns:
            Dict[str, Any]: The updated recipe details.
        """
        try:
            logger.info({"message": "Marking recipe as last made", "slug": slug})
            return mealie.update_recipe_last_made(slug)
        except Exception as e:
            error_msg = f"Error updating recipe last made '{slug}': {str(e)}"
            logger.error({"message": error_msg})
            logger.debug({"message": "Error traceback", "traceback": traceback.format_exc()})
            raise ToolError(error_msg)


