# Tests

Two test scripts covering all 53 MCP tools at two layers.

## Setup

```bash
cp tests/.env.testing.template tests/.env.testing
# Edit tests/.env.testing with your Mealie URL and a temporary API key
```

Create the temporary API key in Mealie under **Profile → API Tokens**. Delete it after testing.

## Script 1 — MealieFetcher (`test_fetcher.py`)

Tests every mixin method directly against the Mealie API. No MCP server required.

```bash
python tests/test_fetcher.py
```

**What it tests:**
- Every `MealieFetcher` method (correct endpoints, parameter mapping, response shapes)
- Full create → read → update → delete cycle for recipes, foods, shopping lists, and meal plans
- Cleanup of all test artifacts using `__test_*` naming convention

**Requirements:**
- `MEALIE_BASE_URL` and `MEALIE_API_KEY` set in `tests/.env.testing`
- External Mealie address (not internal Docker network)

## Script 2 — MCP Server (`test_mcp_server.py`)

Tests every tool via the MCP protocol against a running server instance.

```bash
docker compose up -d
python tests/test_mcp_server.py
```

**What it tests:**
- All 53 tools are registered (`session.list_tools()`)
- Every tool can be called and returns a valid response
- Restricted delete guards reject non-test slugs/names
- Full create → read → update → delete cycle via MCP tool calls

**Requirements:**
- MCP server running in Docker (`docker compose up -d`)
- `MCP_SERVER_URL` set in `tests/.env.testing` (default: `http://localhost:8000/mcp`)
- Server's own `.env` must have valid `MEALIE_BASE_URL` and `MEALIE_API_KEY`

## Test naming convention

All test artifacts use `__test_*` naming so they are visually obvious in the Mealie UI and the restricted delete guards can identify them:

| Artifact | Name |
|----------|------|
| Recipe | `__test_recipe__` → slug `test-recipe` |
| Recipe copy | `__test_recipe_copy__` → slug `test-recipe-copy` |
| Food A | `__test_food_a__` |
| Food B | `__test_food_b__` |
| Shopping list | `__test_shopping_list__` |
| Meal plan | date `2099-01-01` |

## Restricted delete tools

Two tools exist exclusively for the test suite:

- `delete_test_recipe(slug)` — only deletes slugs starting with `test-`
- `delete_test_food(food_id)` — looks up the food, only deletes if name starts with `__test_`

Any attempt to use these tools on real data is rejected with an error.
