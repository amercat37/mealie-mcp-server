# Changelog

All notable changes to this project will be documented here.

---

## [1.0.9] — 2026-05-28

### Added

- `tests/LLM_PROMPT.md` — pasteable prompt for manual LLM integration testing. Instructs Claude or ChatGPT to call all read-only MCP tools in order, report PASS/FAIL per tool with full error and raw JSON on failure, and print a summary.

---

## [1.0.8] — 2026-05-28

### Fixed

- `src/models/recipe.py` — `totalTime`, `prepTime`, `cookTime`, and `performTime` corrected from `Optional[int]` to `Optional[str]` in the `Recipe` read model. Mealie returns these as plain text strings (e.g. `"40 minutes"`); the wrong type caused `get_recipe_concise` to throw a Pydantic validation error on any recipe with time fields set.

### Tests

- `tests/test_mcp_server.py` — test recipe now includes `prepTime`, `performTime`, `totalTime`, `recipeServings`, and `recipeYieldQuantity`; added `get_recipe_concise includes totalTime` assertion to catch this class of regression.

---

## [1.0.7] — 2026-05-28

### Fixed

- `src/server.py` — added `/.well-known/oauth-authorization-server` and `/.well-known/openid-configuration` custom routes that proxy Authentik's OIDC discovery document. MCP clients that use these endpoints for token endpoint discovery (instead of `/.well-known/oauth-protected-resource`) were falling back to a bare `/mcp` request with an expired token, forcing a full manual re-authorization on every access token expiry. Confirmed by 43 `authorize_application` events in Authentik with zero `refresh_token` grants. Both endpoints are cached in memory after the first fetch.

---

## [1.0.6] — 2026-05-15

### Fixed

- `src/models/recipe.py` — added `recipeYieldQuantity: Optional[int]` to `RecipeCreate`. Previously missing, so the field was always 0 regardless of what the LLM provided.
- `src/tools/recipe_tools.py` — `recipeYieldQuantity` is now written to the PATCH payload. Also corrected the docstring: `recipeServings` (people served), `recipeYieldQuantity` (total output, e.g. 6 fillets), and `recipeYield` (unit + per-serving text) are three independent fields, not duplicates of each other. Nutrition values are per serving.
- `src/prompts.py` (`recipe_builder`) — yield instructions updated to match: three independent fields with correct semantics and examples (e.g. 6 fillets / 2 servings / "fillets (3 fillets per serving)").

---

## [1.0.5] — 2026-05-15

### Fixed

- `src/prompts.py` (`recipe_builder`) — Step 2 time format corrected from ISO 8601 (`"PT30M"`) to plain text (`"30 minutes"`, `"1 hour"`).
- `src/prompts.py` (`recipe_builder`) — Step 2 yield updated to describe all three fields: servings count (int), yield quantity (int), and yield text (e.g. `"burgers (1 burger per serving)"`).
- `src/prompts.py` (`recipe_builder`) — Step 2 nutrition changed from optional to required; all eleven fields must be populated with estimates if exact values are unknown.
- `src/prompts.py` (`recipe_builder`) — Step 3 food resolution updated to reflect that `create_recipe` auto-creates unknown foods; manual `create_food` is now described as optional, only needed when a shopping list label should be assigned upfront.

---

## [1.0.4] — 2026-05-15

### Fixed

- `src/tools/recipe_tools.py` (`create_recipe`) — `settings.showNutrition` is now set to `true` in the PATCH whenever nutrition data is provided. Previously the nutrition section was always hidden in the Mealie UI regardless of whether values were present.
- `src/models/recipe.py` — `prepTime`, `performTime`, and `totalTime` comments corrected from ISO 8601 (`"PT30M"`) to plain text (`"30 minutes"`, `"1 hour"`), matching what Mealie actually accepts and displays.
- `src/models/recipe.py` — `recipeYield` comment updated to reflect the three-field pattern: `recipeServings` (int) + `recipeYieldQuantity` (int) + `recipeYield` text (e.g. `"burgers (1 burger per serving)"`).

### Changed

- `create_recipe` docstring — added step-by-step instructions for yield (all three fields), time format (plain text), and nutrition (all eleven fields required, estimate if unknown).

---

## [1.0.3] — 2026-05-15

### Fixed

- `src/tools/recipe_tools.py` (`create_recipe`) — unknown ingredient foods are now auto-created via `POST /api/foods` before the recipe PATCH. Previously a name-only food object (no `id`) was sent, causing Mealie to return a 500 (`ValueError: Expected 'id' to be provided for food`). Foods are cached in `food_lookup` for the duration of the call so the same unknown food is only created once per recipe.
- `src/tools/recipe_tools.py` (`create_recipe`) — unknown ingredient units are now silently dropped instead of sending a name-only unit object, which carried the same 500 risk. No `create_unit` endpoint exists in Mealie.

### Tests

- `tests/test_fetcher.py` — added negative test: `patch_recipe` with a name-only food (no `id`) must return 500, documenting the Mealie requirement that drove the fix above.
- `tests/test_mcp_server.py` — added end-to-end test: `create_recipe` with `__test_auto_food__` as an ingredient food; verifies the recipe succeeds and the food appears in the catalog, then cleans up both.

---

## [1.0.2] — 2026-05-14

### Fixed

- `src/prompts.py` (`shopping_trip`) — removed hardcoded store names from the prompt; assistant now infers the store from context rather than defaulting to specific retailers.

---

## [1.0.1] — 2026-05-14

### Added

- **Automated test suite** under `tests/`:
  - `test_fetcher.py` — tests every `MealieFetcher` mixin method directly against the Mealie API; no MCP server required
  - `test_mcp_server.py` — connects to the running MCP server via the MCP protocol and tests every tool end-to-end
  - `tests/README.md` — setup and usage instructions
- **`.env.testing.template`** — configuration template for test environment
- **`delete_food`** mixin method added to `FoodsMixin`

### Changed

- `delete_test_recipe` and `delete_test_food` removed from MCP tool registration — test suite now calls `MealieFetcher` methods directly; tool count 53 → 51
- `src/mealie/cookbooks.py`, `src/mealie/organizers.py` — corrected `page: int = None` to `page: Optional[int] = None` on all pagination params
- `src/tools/recipe_tools.py` — `food_lookup` now guards against foods with missing `name` field (prevents KeyError)
- `src/models/recipe.py` — extracted `RecipeNutritionCreate` model and moved it above `RecipeCreate` to eliminate forward reference
- `src/prompts.py` (`recipe_builder`) — Step 3 now instructs the assistant to call `get_labels` and assign a `label_id` when creating a new food entry
- `USAGE_EXAMPLES.md` — added sections for all tools and prompts introduced in v1.0.0: `recipe_builder`, `create_recipe`, `duplicate_recipe`, `get_empty_categories`, `get_empty_tags`, `create_food`, `merge_foods`
- `API_COVERAGE.md` — corrected Recipe Operations header; removed duplicate endpoint entry

---

## [1.0.0] — 2026-05-12

Initial release.

### Features

- **48 MCP tools** covering recipes, shopping lists, meal plans, categories, tags, foods, organizers, and cookbooks
- **5 server prompts**: `weekly_meal_plan`, `shopping_trip`, `cooking_session`, `weekly_review`, `nutrition_summary`
- **1 guided creation prompt**: `recipe_builder` — step-by-step recipe creation following existing category/tag/tool conventions
- **OAuth 2.0 bearer authentication** via [Authentik](https://goauthentik.io/) — JWT validation using OIDC discovery + JWKS; opt-in (server runs unauthenticated when `AUTHENTIK_ISSUER` is not set)
- **Docker + HTTP transport** — `Dockerfile` and `docker-compose.yml` for containerised deployment; server listens on port `8000` at `/mcp`
- **3 Pydantic models**: `RecipeCreate`, `RecipeIngredientCreate`, `RecipeInstructionCreate`
- **GitHub templates**: PR template and bug/feature issue templates under `.github/`

### Origin

Based on [rldiao/mealie-mcp-server](https://github.com/rldiao/mealie-mcp-server). See [README.md](README.md) for the full list of changes from the original.
