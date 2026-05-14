# Changelog

All notable changes to this project will be documented here.

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
