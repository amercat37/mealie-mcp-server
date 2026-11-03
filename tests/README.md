# Tests

Seven automated scripts plus two manual LLM prompts:

- **Four unit scripts** — no live infrastructure (`test_auth.py`, `test_client_retry.py`,
  `test_recipe_model.py`, `test_tool_helpers.py`)
- **Three integration scripts** — cover the MCP tools at two layers
  (`test_fetcher.py` direct, `test_mcp_server.py` via the MCP protocol) plus a focused
  create_recipe hardening check (`test_recipe_create_fix.py`)
- **Two manual LLM prompts** — `LLM_PROMPT.md` (read-only, every read tool) and
  `LLM_PROMPT_CREATE.md` (mutating — one recipe create, verified per-field)

## Recommended run order

Run the unit scripts first (fast, touch nothing), then the integration scripts,
then the manual LLM prompts:

```bash
python tests/test_auth.py            # unit — no infra
python tests/test_client_retry.py    # unit — no infra
python tests/test_recipe_model.py    # unit — no infra (RecipeCreate model, recipe times)
python tests/test_tool_helpers.py    # unit — no infra (week alignment, lastMade fallback, tool output shapes)
python tests/test_fetcher.py         # integration — live Mealie
docker compose -f tests/docker-compose.yml up -d --build
python tests/test_mcp_server.py      # integration — live Mealie via MCP
python tests/test_recipe_create_fix.py   # integration — create_recipe hardening, via MCP
docker compose -f tests/docker-compose.yml down
# then paste tests/LLM_PROMPT.md (read-only) into Claude/ChatGPT with the MCP server connected
# and, after the create_recipe fix is deployed, tests/LLM_PROMPT_CREATE.md (mutating — delete its recipe after)
```

> The integration scripts create and delete real recipes/foods/lists/meal plans.
> They are self-cleaning within a single run and everything is `__test_*`-named,
> so they are safe to run against a production Mealie — just use a temporary API
> key and delete it afterwards.

## Setup

Only the integration scripts (1 and 2) need this; the unit scripts and the LLM
prompt do not.

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
docker compose -f tests/docker-compose.yml up -d --build
python tests/test_mcp_server.py
```

**What it tests:**
- All 51 tools are registered (`session.list_tools()`)
- Every tool can be called and succeeds (`isError` is false; failures print the error text)
- Full create → read → update cycle via MCP tool calls, including Mealie v3.30 structured
  recipe times, household `lastMade` and whole-week meal plan entries
- Cleanup of test artifacts via direct fetcher calls (delete is not an MCP tool)

**Requirements:**
- MCP server running in Docker (`docker compose -f tests/docker-compose.yml up -d --build`)
- `MCP_SERVER_URL` set in `tests/.env.testing` (default: `http://localhost:8000/mcp`)
- Server's own `.env` must have valid `MEALIE_BASE_URL` and `MEALIE_API_KEY`

## Script 3 — Auth token verifier (`test_auth.py`)

Unit-tests `src/auth.py` (Authentik JWT verification). Needs **no live
infrastructure** — no Mealie, no Authentik, no running server, no
`.env.testing`. It mints its own RS256 keys with `joserfc` and stubs the JWKS
cache.

```bash
python tests/test_auth.py
```

**What it tests:**
- Audience enforcement — accepts a matching `aud`, rejects a wrong or missing one
- RS256 algorithm pinning — rejects an `HS256`-forged token (alg-confusion)
- Signing-key rotation — an unknown `kid` forces exactly one JWKS refetch
- Forced-refetch rate limiting (`_JWKS_MIN_REFETCH`)
- Claim validation — `exp`, `nbf`, and `iss` (incl. trailing-slash normalization)
- `build_token_verifier()` fails closed when `AUTHENTIK_AUDIENCE` is unset

**Requirements:**
- None beyond the project's own dependencies (`joserfc`, already required)

## Script 4 — Request retry (`test_client_retry.py`)

Unit-tests the `RemoteProtocolError` retry logic in `src/mealie/client.py`. Needs
**no live infrastructure** — it builds a `MealieClient` with a stubbed httpx client
(bypassing the constructor's connection check) and drives `_handle_request` directly.

```bash
python tests/test_client_retry.py
```

**What it tests:**
- An idempotent method (GET/PATCH/DELETE) is retried once on a stale-connection
  error and can succeed on the retry
- A non-idempotent **POST** is **not** retried — it raises after exactly one attempt,
  so a request already processed server-side is never duplicated (e.g. `recipe` /
  `recipe-1`)

**Requirements:**
- None beyond the project's own dependencies (`httpx`, already required)

## Script 5 — RecipeCreate model (`test_recipe_model.py`)

Unit-tests the `create_recipe` input model. Needs **no live infrastructure** — it
drives `RecipeCreate` / `RecipeNutritionCreate` directly and inspects the FastMCP tool
schema.

```bash
python tests/test_recipe_model.py
```

**What it tests:**
- Natural-name aliases map to Mealie fields (`categories`→`recipeCategory`,
  `cookTime`→`performTime`, `servings`→`recipeServings`, `sourceUrl`→`orgURL`, …)
- `extra="forbid"` rejects unknown keys at the top level **and** nested
  (ingredient/instruction/nutrition) — no silent drop
- Nutrition values normalize to bare numbers (`"1,200 mg"`→`"1200"`)
- The FastMCP tool schema advertises canonical names + `additionalProperties: false`,
  and an unknown key returns an `isError` (retryable) result
- Recipe times: text → seconds parsing ("1 hour 30 minutes", "90 min", "PT1H30M"),
  bare numbers rejected, non-durations ("overnight") kept as text, seconds → readable text,
  and the create payload storing seconds only

**Requirements:**
- None beyond the project's own dependencies

## Script 6 — create_recipe hardening, end-to-end (`test_recipe_create_fix.py`)

Integration test that exercises the create_recipe fix through the **real MCP protocol**
against a running server. Self-cleaning (`__test_fix_*`).

```bash
docker compose -f tests/docker-compose.yml up -d --build
python tests/test_recipe_create_fix.py
```

**What it tests:**
- Sending alias field names **and** a category as a display name ("Sauce") round-trips
  — categories/ingredients/instructions/cook time/servings/nutrition all land
- Nutrition unit suffixes are stripped end-to-end
- An unknown key returns `isError` and creates **no** stub recipe

**Requirements:**
- Same as Script 2 (`MCP_SERVER_URL` + a running server + Mealie creds)

## Script 7 — Tool helpers (`test_tool_helpers.py`)

Unit-tests tool logic against stand-in objects. Needs **no live infrastructure**.

```bash
python tests/test_tool_helpers.py
```

**What it tests:**
- Whole-week meal plan entries align to every household `firstDayOfWeek` setting
  (0=Sunday … 6=Saturday) and span exactly 7 days — the integration tests only see the
  live household's own setting
- `get_recipe_concise` / `get_recipe_detailed` return readable times and the household
  `lastMade`, and still return the recipe when the `lastMade` lookup fails
- Every shopping list tool that returns a whole list trims `recipeReferences` to
  `recipeId`, `name`, `slug`, `recipeQuantity`
- `update_shopping_list_label_settings` reorders by label name (named first, the rest
  keep their order) and sends nothing for an unknown name or an empty list
- `create_mealplan` / `create_mealplan_bulk` return trimmed entries with ids, check every
  bulk entry before creating any, and report exactly what was created on a partial failure

**Requirements:**
- None beyond the project's own dependencies

## Manual — LLM integration prompt (`LLM_PROMPT.md`)

Not a script. Paste the body of `tests/LLM_PROMPT.md` into Claude or ChatGPT with
the Mealie MCP server connected. It instructs the model to call every **read-only**
tool once — chaining IDs/slugs from earlier calls — and report PASS/FAIL per tool.

**What it tests:**
- Every read-only tool is reachable and returns a valid response through a real
  LLM client (the actual usage path), not just the protocol

**Requirements:**
- The MCP server connected to an LLM client (no `.env.testing` needed)
- Entirely read-only — the safest test to run against production. Note ChatGPT's
  safety filter may false-positive on some read-only tools (see the file); treat
  those as platform noise, not server failures.

## Manual — LLM create acceptance test (`LLM_PROMPT_CREATE.md`)

Not a script, and **mutating**. Paste the body into Claude or ChatGPT with the MCP
server connected. It has the model create one recipe from fixed data (engineered to
stress alias field names, an unknown unit, bare-unit yield, and per-serving nutrition),
read it back, and report PASS/FAIL for 9 field groups. Exercises the real write seam
that automated tests can't — a real model choosing field names → the deployed server.

**What it tests:**
- End-to-end that a real LLM's `create_recipe` produces a *complete* recipe (the seam
  the silent-field-drop bug lived in). Best run **after** the create_recipe fix is deployed.

**Requirements:**
- The MCP server connected to an LLM client
- **Creates one recipe (`__test_llm_create__`) and does not delete it** — remove it in
  the Mealie UI when finished.

## Test naming convention

All test artifacts use `__test_*` naming so they are visually obvious in the Mealie UI.
The integration scripts delete every one of these within a single run:

| Artifact | Name |
|----------|------|
| Recipe | `__test_recipe__` → slug `test-recipe` |
| Recipe copy | `__test_recipe_copy__` → slug `test-recipe-copy` |
| Auto-food recipe | `__test_recipe_auto_food__` → slug `test-recipe-auto-food` |
| Fractional recipe | `__test_recipe_fractional__` → slug `test-recipe-fractional` |
| Unknown-unit recipe | `__test_recipe_unknown_unit__` → slug `test-recipe-unknown-unit` |
| create_recipe-fix recipes | `__test_fix_friendly__` / `__test_fix_bad__` (Script 6) |
| LLM create acceptance recipe | `__test_llm_create__` (manual — delete yourself) |
| Food A / B | `__test_food_a__` / `__test_food_b__` |
| Auto-created food | `__test_auto_food__` |
| Unknown-unit foods | `__test_food_uu_a__` / `__test_food_uu_b__` |
| Shopping list | `__test_shopping_list__` |
| Meal plan | date `2099-01-01` |
