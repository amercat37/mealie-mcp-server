# Changelog

All notable changes to this project will be documented here.

---

## [1.4.6] — 2026-05-15

### Fixed

- `src/models/recipe.py` — added `recipeYieldQuantity: Optional[int]` to `RecipeCreate`. Previously missing, so the field was always 0 regardless of what the LLM provided.
- `src/tools/recipe_tools.py` — `recipeYieldQuantity` is now written to the PATCH payload. Also corrected the docstring: `recipeServings` (people served), `recipeYieldQuantity` (total output, e.g. 6 fillets), and `recipeYield` (unit + per-serving text) are three independent fields, not duplicates of each other. Nutrition values are per serving.
- `src/prompts.py` (`recipe_builder`) — yield instructions updated to match: three independent fields with correct semantics and examples (e.g. 6 fillets / 2 servings / "fillets (3 fillets per serving)").

---

## [1.4.5] — 2026-05-15

### Fixed

- `src/prompts.py` (`recipe_builder`) — Step 2 time format corrected from ISO 8601 (`"PT30M"`) to plain text (`"30 minutes"`, `"1 hour"`).
- `src/prompts.py` (`recipe_builder`) — Step 2 yield updated to describe all three fields: servings count (int), yield quantity (int), and yield text (e.g. `"burgers (1 burger per serving)"`).
- `src/prompts.py` (`recipe_builder`) — Step 2 nutrition changed from optional to required; all eleven fields must be populated with estimates if exact values are unknown.
- `src/prompts.py` (`recipe_builder`) — Step 3 food resolution updated to reflect that `create_recipe` auto-creates unknown foods; manual `create_food` is now described as optional, only needed when a shopping list label should be assigned upfront.

---

## [1.4.4] — 2026-05-15

### Fixed

- `src/tools/recipe_tools.py` (`create_recipe`) — `settings.showNutrition` is now set to `true` in the PATCH whenever nutrition data is provided. Previously the nutrition section was always hidden in the Mealie UI regardless of whether values were present.
- `src/models/recipe.py` — `prepTime`, `performTime`, and `totalTime` comments corrected from ISO 8601 (`"PT30M"`) to plain text (`"30 minutes"`, `"1 hour"`), matching what Mealie actually accepts and displays.
- `src/models/recipe.py` — `recipeYield` comment updated to reflect the three-field pattern: `recipeServings` (int) + `recipeYieldQuantity` (int) + `recipeYield` text (e.g. `"burgers (1 burger per serving)"`).

### Changed

- `create_recipe` docstring — added step-by-step instructions for yield (all three fields), time format (plain text), and nutrition (all eleven fields required, estimate if unknown).

---

## [1.4.3] — 2026-05-15

### Fixed

- `src/tools/recipe_tools.py` (`create_recipe`) — unknown ingredient foods are now auto-created via `POST /api/foods` before the recipe PATCH. Previously a name-only food object (no `id`) was sent, causing Mealie to return a 500 (`ValueError: Expected 'id' to be provided for food`). Foods are cached in `food_lookup` for the duration of the call so the same unknown food is only created once per recipe.
- `src/tools/recipe_tools.py` (`create_recipe`) — unknown ingredient units are now silently dropped instead of sending a name-only unit object, which carried the same 500 risk. No `create_unit` endpoint exists in Mealie.
- `src/prompts.py` (`shopping_trip`) — removed hardcoded store names from the prompt; assistant now infers the store from context rather than defaulting to specific retailers.

### Tests

- `tests/test_fetcher.py` — added negative test: `patch_recipe` with a name-only food (no `id`) must return 500, documenting the Mealie requirement that drove the fix above.
- `tests/test_mcp_server.py` — added end-to-end test: `create_recipe` with `__test_auto_food__` as an ingredient food; verifies the recipe succeeds and the food appears in the catalog, then cleans up both. Pre-test cleanup also covers the `test-recipe-auto-food` slug.

---

## [1.4.2] — 2026-05-14

### Changed

- `delete_test_recipe` and `delete_test_food` removed from MCP tool registration — these were only ever used by the test suite, which now calls `MealieFetcher.delete_recipe()` / `delete_food()` directly; the underlying mixin methods are unchanged
- `tests/test_mcp_server.py` — pre-test cleanup and post-test cleanup now use the fetcher directly instead of calling MCP tools; guard tests removed (no MCP tools to guard)
- Tool count: 53 → 51; API coverage updated accordingly in `API_COVERAGE.md`, `USAGE_EXAMPLES.md`, and `tests/README.md`

---

## [1.4.1] — 2026-05-14

### Fixed

- `src/mealie/cookbooks.py`, `src/mealie/organizers.py` — corrected `page: int = None` to `page: Optional[int] = None` on all pagination params
- `src/tools/recipe_tools.py` — `food_lookup` now guards against foods with missing `name` field (prevents KeyError)
- `src/models/recipe.py` — extracted `RecipeNutritionCreate` model (subset of fields for recipe creation) and moved it above `RecipeCreate` to eliminate the forward reference string quote
- `API_COVERAGE.md` — corrected Recipe Operations header from "6/14" to "7/14"; removed duplicate `DELETE /api/recipes/{slug}` from the Not Implemented list

### Changed

- `src/prompts.py` (`recipe_builder`) — Step 3 now instructs the assistant to call `get_labels` and assign a `label_id` (shopping list aisle) when creating a new food entry
- `USAGE_EXAMPLES.md` — added sections for all tools and prompts introduced in v1.3.0 and v1.4.0: `recipe_builder` prompt, `create_recipe`, `duplicate_recipe`, `get_empty_categories`, `get_empty_tags`, `create_food`, `merge_foods`

---

## [1.4.0] — 2026-05-14

### Added

- **2 restricted delete tools** for use exclusively by the test suite:
  - `delete_test_recipe(slug)` — deletes only slugs starting with `test-`
  - `delete_test_food(food_id)` — looks up food name first; deletes only names starting with `__test_`
- **Automated test suite** under `tests/`:
  - `test_fetcher.py` — tests every `MealieFetcher` mixin method directly against the Mealie API; no MCP server required
  - `test_mcp_server.py` — connects to the running MCP server via the MCP protocol and tests every tool end-to-end
  - `tests/README.md` — setup and usage instructions
- **`.env.testing.template`** — configuration template for test environment (external Mealie URL, temporary API key, debug logging, MCP server URL)
- **`delete_food`** mixin method added to `FoodsMixin` (backing `delete_test_food`)

### Changed

- API coverage: 51 tools (restricted delete tools removed from MCP registration; test suite calls the fetcher directly)

---

## [1.3.0] — 2026-05-14

### Added

- **6 new MCP tools** for recipe creation and food library management:
  - Recipes: `create_recipe`, `duplicate_recipe`
  - Foods: `create_food`, `merge_foods`
  - Categories: `get_empty_categories` (restored)
  - Tags: `get_empty_tags` (restored)
- **1 new server prompt**: `recipe_builder` — guided recipe creation that follows existing category/tag/tool conventions, matches ingredients to the food library, defaults to the "My Recipes" cookbook (`my-recipes` tag)
- **3 new Pydantic models**: `RecipeCreate`, `RecipeIngredientCreate`, `RecipeInstructionCreate`

### Changed

- `create_recipe` tool performs POST (create skeleton) + PATCH (fill all fields) automatically — the caller provides a single `RecipeCreate` payload and gets a fully populated recipe back
- Food slug/name resolution happens inside `create_recipe` — categories, tags, tools resolved to full objects; food names fuzzy-matched against the library before any new food is created
- API coverage improves from 45 tools (53%) to 51 tools (~59%)

---

## [1.2.0] — 2026-05-14

### Added

- **17 new MCP tools** across meal plans, recipes, shopping lists, cookbooks, and organizers:
  - Meal plans: `update_mealplan`, `delete_mealplan`
  - Recipes: `get_recipe_comments`, `create_recipe_comment`, `get_recipe_timeline`, `get_recipe_share_tokens`, `create_recipe_share_token`, `get_recipe_exports`
  - Shopping lists: `update_shopping_list`, `update_shopping_list_label_settings`, `add_recipes_to_shopping_list_bulk`
  - Household: `get_cookbooks`
  - Organizers: `get_cooking_tools`, `get_units`, `get_labels`
- **5 server prompts**: `weekly_meal_plan` (rewritten), `shopping_trip`, `cooking_session`, `weekly_review`, `nutrition_summary`
- **2 new Pydantic models**: `RecipeComment`, `RecipeCommentCreate`
- **2 new mixin files**: `src/mealie/organizers.py`, `src/mealie/cookbooks.py`
- **2 new tool files**: `src/tools/organizers_tools.py`, `src/tools/cookbooks_tools.py`
- **GitHub templates**: PR template and bug/feature issue templates under `.github/`

### Removed

- `get_empty_categories` — housekeeping tool with no practical use case
- `get_empty_tags` — housekeeping tool with no practical use case
- `src/mealie/user.py`, `src/mealie/group.py` — dead code; methods were inherited but never called by any tool

### Changed

- `weekly_meal_plan` prompt fully rewritten with configurable variables (`days`, `tags`, `meals`, `notes`), sandwich rules, leftover rules, and correct Mealie category slugs
- API coverage improves from 31 tools (48%) to 45 tools (73%)

---

## [1.0.0] — 2026-05-12

Initial release.

### Features

- **31 MCP tools** covering recipes, shopping lists, categories (read-only), tags (read-only), foods (read-only), and meal plans
- **OAuth 2.0 bearer authentication** via [Authentik](https://goauthentik.io/) — JWT validation using OIDC discovery + JWKS; opt-in (server runs unauthenticated when `AUTHENTIK_ISSUER` is not set)
- **Docker + HTTP transport** — `Dockerfile` and `docker-compose.yml` for containerised deployment; server listens on port `8000` at `/mcp`
- **Read-only policy on categories and tags** — recipe write tools (create, update, delete) removed to limit the blast radius of an exposed MCP endpoint; shopping list and meal plan write tools retained as the primary interactive use case

### Origin

Based on [rldiao/mealie-mcp-server](https://github.com/rldiao/mealie-mcp-server). See [README.md](README.md) for the full list of changes from the original.
