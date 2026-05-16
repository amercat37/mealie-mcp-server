import logging
import traceback
from typing import Any, Dict, List, Optional

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError

from mealie import MealieFetcher
from models.recipe import Recipe, RecipeCreate

logger = logging.getLogger("mealie-mcp")


def register_recipe_tools(mcp: FastMCP, mealie: MealieFetcher) -> None:
    """Register all recipe-related tools with the MCP server."""

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
            Dict[str, Any]: Recipe summaries with details like ID, name, description, and image information.
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
            return mealie.get_recipes(
                search=search,
                page=page,
                per_page=per_page,
                categories=categories,
                tags=tags,
                require_all_tags=require_all_tags,
                require_all_categories=require_all_categories,
            )
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
            Dict[str, Any]: Comprehensive recipe details including ingredients, instructions,
                nutrition information, notes, and associated metadata.
        """
        try:
            logger.info({"message": "Fetching recipe", "slug": slug})
            return mealie.get_recipe(slug)
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
            Dict[str, Any]: Concise recipe summary with essential fields.
        """
        try:
            logger.info({"message": "Fetching recipe", "slug": slug})
            recipe_json = mealie.get_recipe(slug)
            recipe = Recipe.model_validate(recipe_json)
            return recipe.model_dump(
                include={
                    "name",
                    "slug",
                    "recipeServings",
                    "recipeYieldQuantity",
                    "recipeYield",
                    "totalTime",
                    "rating",
                    "recipeIngredient",
                    "lastMade",
                },
                exclude_none=True,
            )
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
           (e.g. "c" or "cup" → use the existing "cup" unit). If no unit fits, omit it —
           do not invent unit names, as unknown units will be silently dropped.
        4. Always include "my-recipes" in tags (default). Use "the-autoimmune-solution"
           instead if the recipe belongs to that cookbook.

        The tool resolves all slug and name references to IDs automatically before saving.

        Args:
            recipe: RecipeCreate object with name, description, categories (slugs),
                tags (slugs), tools (slugs), ingredients (food/unit names), instructions,
                timing, servings, source URL, nutrition, and notes.

        Returns:
            Dict[str, Any]: The fully created recipe as returned by Mealie
        """
        try:
            logger.info({"message": "Creating recipe", "name": recipe.name})

            # Step 1: POST to create skeleton, get slug
            slug = mealie.create_recipe(recipe.name)
            if not isinstance(slug, str):
                slug = slug.get("slug", slug)

            # Step 2: Resolve categories, tags, tools slugs → full objects
            def resolve_organizer(items: List[str], fetch_fn) -> List[Dict[str, Any]]:
                if not items:
                    return []
                all_items = fetch_fn(per_page=200).get("items", [])
                lookup = {i["slug"]: i for i in all_items}
                return [lookup[s] for s in items if s in lookup]

            resolved_categories = resolve_organizer(recipe.recipeCategory, mealie.get_categories)
            resolved_tags = resolve_organizer(recipe.tags, mealie.get_tags)
            resolved_tools = resolve_organizer(recipe.tools, mealie.get_organizer_tools)

            # Step 3: Resolve ingredient food names and unit names → full objects
            all_foods = mealie.get_foods(per_page=500).get("items", [])
            food_lookup = {f["name"].lower(): f for f in all_foods if f.get("name")}

            all_units = mealie.get_organizer_units(per_page=200).get("items", [])
            unit_lookup = {u["name"].lower(): u for u in all_units}
            unit_lookup.update({u.get("abbreviation", "").lower(): u for u in all_units if u.get("abbreviation")})

            resolved_ingredients = []
            for ing in recipe.recipeIngredient:
                resolved: Dict[str, Any] = {}
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
                    # Unknown units are dropped — Mealie requires a unit id on PATCH
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
            if recipe.prepTime:
                patch_data["prepTime"] = recipe.prepTime
            if recipe.performTime:
                patch_data["performTime"] = recipe.performTime
            if recipe.totalTime:
                patch_data["totalTime"] = recipe.totalTime
            if recipe.recipeYield:
                patch_data["recipeYield"] = recipe.recipeYield
            if recipe.recipeServings:
                patch_data["recipeServings"] = recipe.recipeServings
            if recipe.orgURL:
                patch_data["orgURL"] = recipe.orgURL
            if recipe.nutrition:
                patch_data["nutrition"] = recipe.nutrition.model_dump(exclude_none=True)
            if recipe.notes:
                patch_data["notes"] = recipe.notes

            # Step 5: PATCH with full data
            return mealie.patch_recipe(slug, patch_data)
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
            return mealie.duplicate_recipe(slug, name=name)
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


