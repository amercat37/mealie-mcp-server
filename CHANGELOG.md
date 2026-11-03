# Changelog

All notable changes to this project will be documented here.

---

## [1.0.24] — 2026-11-03

Follow-ups from the v1.0.23 assistant test runs.

### Changed

- **Shopping lists no longer embed whole recipes.** Each `recipeReferences` entry carried a full recipe summary (description, tags, categories, times…) — most of the list's size, and the times showed as `null`. Every tool that returns a whole list (`get_shopping_lists`, `get_shopping_list`, `create_shopping_list`, `update_shopping_list`, `delete_shopping_list`, `add_recipe_to_shopping_list`, `remove_recipe_from_shopping_list`, `add_recipes_to_shopping_list_bulk`) now returns `{recipeId, name, slug, recipeQuantity}` per recipe. Only the tool output is trimmed; the rename still sends Mealie the full list.
- **`update_shopping_list_label_settings` takes label names in store order.** It previously passed raw label-setting objects through, and its description said each needed only `labelId` + `position` — Mealie also requires `id` and `shoppingListId`, so following the description always failed. The tool now takes `labels`: names as `get_labels` returns them (case-insensitive; a label id is accepted too). Named labels go first and the rest keep their current relative order. Every name is checked before anything is sent: an unknown one returns an error listing the list's real labels and changes nothing. It returns only the resulting `labelOrder`.
- **`create_mealplan_bulk` returns the created entries.** It returned only a message, so an assistant had to call `get_all_mealplans` to find the ids of what it had just made. It now returns `created`: each entry's `id`, `date`, `endDate` (week entries), `entryType`, and `title` or `recipeId` / `recipeName` / `recipeSlug`, in the order given.
  - **Every entry is checked before any is created** — date format, `entry_type` (all seven Mealie types: breakfast, lunch, dinner, side, snack, drink, dessert), a recipe or title, a recipe UUID, and no unknown fields (`entryType` was silently ignored, creating a breakfast). One bad entry creates nothing and the error names it.
  - **Partial failures are reported precisely.** Entries are created one at a time; if Mealie fails partway, the error lists the ids created, the entry that failed and those not attempted, so a retry doesn't duplicate the first ones.
- **`create_mealplan` returns the same trimmed entry** instead of Mealie's full entry with the embedded recipe summary, and rejects a bad `entry_type` before calling Mealie.
- **No label names hard-coded in tool descriptions or prompts.** The `shopping_trip` prompt listed one Mealie's labels alphabetically and told the assistant to use them in that order (working against the store order, and missing a label). It, the `recipe_builder` prompt and `get_labels` now send the assistant to `get_labels` for the exact names and say never to invent one.

### Fixed

- **`create_recipe` ingredient ids changed on every read.** Ingredients were sent without a `referenceId`; Mealie stores none and makes up a new random one each time the recipe is read, so the create response and every later read disagreed (an assistant comparing them flagged it). `create_recipe` now sends an id per ingredient, as Mealie's own editor does, so it is stored and stays the same. Recipes saved in the Mealie editor were never affected.
- `update_mealplan` / `delete_mealplan` typed `entry_id` as text, but meal plan ids are numbers, so passing the id exactly as `create_mealplan` / `get_all_mealplans` returned it (`12`) failed validation and the assistant had to retry with `"12"`. Both now accept a number or text.

### Tests

- `tests/LLM_PROMPT_WRITE.md` (new) — the shopping list and meal plan write prompt from the v1.0.23 assistant runs, saved and updated for this release: trimmed recipe references, reordering by label name and the unknown-name rejection, a numeric `entry_id`, bulk create ids and a rejected bulk batch. It deletes everything it creates. `tests/README.md` documents it.
- `tests/LLM_PROMPT_CREATE.md` — the unknown-unit check had stopped testing anything: "slices" was added to the unit catalog, so it resolved as a normal unit and passed. Ingredient 4 is now "2 rashers bacon", sent exactly as given, and a `get_units` pre-check makes the group report NOT TESTED instead of a false PASS if "rashers" is ever added.
- `tests/test_tool_helpers.py` — every list-returning shopping list tool trims `recipeReferences`.
- `tests/test_mcp_server.py` — live check that a list's recipe reference is trimmed and points at the added recipe.
- `tests/test_mcp_server.py` — `create_recipe`'s ingredient `referenceId`s match two later reads.
- `tests/test_mcp_server.py` — `update_mealplan` / `delete_mealplan` are called with both a numeric and a text `entry_id`.
- `tests/test_tool_helpers.py` — label reordering: order, payload fields, case and duplicate handling, id fallback, unknown and empty input send nothing.
- `tests/test_tool_helpers.py` — trimmed meal plan entries, each pre-create check, and the partial-failure report.
- `tests/test_mcp_server.py` — `create_mealplan` / `create_mealplan_bulk` return trimmed entries with ids (and `endDate` for a week entry); a bulk call with one bad entry creates nothing.
- `tests/test_mcp_server.py` — live label reordering on the test list (named first, rest unchanged), unknown-name rejection with nothing changed, empty input rejected.

---

## [1.0.23] — 2026-11-03

Compatibility with **Mealie v3.30.0** (upgraded from v3.16.0). **Now requires Mealie v3.30.0 or later.**

### Changed

- **Recipe times use Mealie's structured durations.** Mealie v3.29 added `prepTimeSeconds` / `performTimeSeconds` / `totalTimeSeconds`, and its upgrade migration moved every parseable text time into them and blanked the legacy text fields — so `get_recipe_concise` lost its time and the other read tools returned `null` times.
  - New `src/recipe_times.py` converts between the two formats.
  - `get_recipes`, `get_recipe_detailed`, `get_recipe_concise`, `create_recipe` and `duplicate_recipe` fill `prepTime` / `performTime` / `totalTime` with readable text built from the seconds (`10800` → `"3 hours"`). A text-only value such as `"overnight"` is returned as stored. The list and detailed tools keep the `*TimeSeconds` numbers too.
  - `create_recipe` stores a duration only as seconds, matching migrated recipes, and keeps the legacy text field only for a non-duration such as `"overnight"`. It accepts text with a unit (`"1 hour 30 minutes"`, `"90 min"`, `"PT1H30M"`) or the `*TimeSeconds` fields (`cookTimeSeconds` is accepted as an alias). A zero time is stored as no time.
  - `create_recipe` **rejects a bare number** such as `"45"` (minutes or hours?) with a validation error asking for a unit, before anything is created.
- **`lastMade` restored.** Mealie v3.29 removed it from the recipe and keeps it per household. `get_recipe_detailed` and `get_recipe_concise` now read it from `GET /api/households/self/recipes/{slug}`; a failed lookup is logged and skipped instead of failing the read.
- **Whole-week meal plan entries** (Mealie v3.30). Mealie hides them from API clients unless asked.
  - `get_all_mealplans` now includes them (`include_week_entries`); a week entry overlapping the date range is returned.
  - `create_mealplan`, `create_mealplan_bulk` and `update_mealplan` take `whole_week`. A week entry is aligned to the household's first-day-of-week preference and ends six days later, as Mealie requires. `update_mealplan` recomputes both ends when the date moves; `whole_week` omitted keeps the entry's current kind.
  - `get_todays_mealplan` is unchanged: Mealie excludes week entries from "today".
  - The `weekly_meal_plan` and `shopping_trip` prompts explain week entries.
- `pyproject.toml` — pin `mcp[cli]<2`. mcp 2.x renamed `FastMCP`, so an unpinned rebuild would install 2.x and the server would crash on startup.

### Fixed

- `get_all_mealplans` date filtering never worked: the server sent `startDate` / `endDate`, which Mealie ignores (it reads `start_date` / `end_date`), so every entry was returned regardless of the range.

### Tests

- `tests/test_mcp_server.py` — 29 checks only tested that a result had content, which an `isError` result also has, so a failing tool passed. They now require `not isError` and print the error text. The empty-list `delete_shopping_list_items_bulk` check (which ended in `or True`) now requires the "cannot be empty" error. Added checks for structured times, readable times in all three read tools, bare-number rejection, `lastMade`, week entries (create, list overlap, move, convert, bulk) and the date filter.
- `tests/test_recipe_model.py` — unit tests for time parsing, formatting and the create payload.
- `tests/test_tool_helpers.py` (new, no live infrastructure) — whole-week alignment for every `firstDayOfWeek` setting, and the recipe read tools when the `lastMade` lookup fails. `tests/README.md` documents it.
- `tests/test_mcp_server.py`, `tests/test_recipe_create_fix.py` — exit with code 0 on a passing run (the `SystemExit` was raised inside the MCP client's async context and wrapped in an exception group, so every run exited 1).
- `tests/LLM_PROMPT_CREATE.md` — time group also checks the stored `*TimeSeconds` values.

---

## [1.0.22] — 2026-07-22

### Fixed

- `src/models/recipe.py` + `src/tools/recipe_tools.py` — `create_recipe` no longer **silently drops** fields whose key doesn't match the model. Previously, when a client sent natural field names (`categories`, `ingredients`, `instructions`, `cookTime`) instead of the exact Mealie names (`recipeCategory`, `recipeIngredient`, `recipeInstructions`, `performTime`), Pydantic's default ignored the unknown keys and the recipe was created missing those whole sections — with no error. Hardened the create path:
  - **Fail loud.** `RecipeCreate` and its nested models (`RecipeIngredientCreate`, `RecipeInstructionCreate`, `RecipeNutritionCreate`) now use `extra="forbid"`, so an unrecognized field returns a clear `isError` result the caller can correct, instead of vanishing.
  - **Accept the natural names.** `categories`/`ingredients`/`instructions`/`cookTime`/`servings`/`sourceUrl` are accepted as aliases and mapped to the canonical Mealie fields (the schema still advertises the canonical names).
  - **Match organizers by slug *or* name.** `resolve_organizer` now matches categories/tags/tools case-insensitively by slug or display name, so a category sent as `"Sauce"` (name, not slug) resolves instead of being silently dropped; any genuinely unmatched value is logged.
  - **Normalize nutrition values** to bare numbers (`"4.9 g"` → `"4.9"`, `"1,200 mg"` → `"1200"`) so Mealie doesn't render a doubled unit.
  - The raw input keys are logged on every `create_recipe` call, so field-name mismatches are diagnosable.

### Added

- `tests/test_recipe_model.py` — deterministic `RecipeCreate` unit tests (aliases, `extra="forbid"` top-level + nested, nutrition normalization, FastMCP schema shape + `isError` on unknown key).
- `tests/test_recipe_create_fix.py` — end-to-end integration test via the MCP protocol (alias + name-not-slug round-trip, nutrition strip, unknown key → `isError` with no stub created; self-cleaning).
- `tests/LLM_PROMPT_CREATE.md` — manual LLM acceptance test that creates one recipe stressing every failure mode and reports per-field PASS/FAIL.

---

## [1.0.21] — 2026-07-22

### Fixed

- `src/tools/recipe_tools.py` — `create_recipe` no longer silently drops an ingredient unit that has no match in Mealie's unit catalog. Previously an unresolvable unit (e.g. "slices") was discarded because Mealie requires a unit id on PATCH, so "2 slices bacon" was stored as "2 bacon" — silent data loss. The unmatched unit text is now appended to the ingredient's `note` (after any existing note) and logged, so the information is preserved for correction on review. Units that do resolve are unchanged — they are still stored structurally. This avoids polluting the unit vocabulary with half-populated, fragmented entries (slice / slices / Slice) that auto-creating a unit per unknown name would produce.
- `src/mealie/client.py` — `_handle_request` no longer retries a **POST** after a `RemoteProtocolError`. The retry (added in 1.0.18 for stale pooled connections) fired for every method, but that error is also raised when the server drops the connection *after* receiving the request — indistinguishable from the never-sent case. For a non-idempotent POST that meant a recipe already created server-side would be created a second time on retry, producing a duplicate (e.g. `chicken-soup` and `chicken-soup-1`). Retries are now limited to idempotent methods (GET/PATCH/DELETE/PUT); a stale-connection failure on a POST surfaces as an error for the caller to retry rather than silently duplicating.

### Added

- `tests/test_mcp_server.py` — regression coverage that creates a recipe with an unresolvable ingredient unit and asserts the unit text is preserved in the note (both the no-prior-note and append-to-existing-note cases) and never leaks into the structured unit field.
- `tests/test_client_retry.py` — unit tests (no live infrastructure) asserting that an idempotent request retries once and can succeed on the retry, while a POST raises after exactly one attempt and is never retried.

---

## [1.0.20] — 2026-07-22

### Changed

- `src/models/recipe.py` — aligned the recipe yield/servings fields with Mealie's own data model. `recipeServings` and `recipeYieldQuantity` are now `float` (were `int`), so fractional values like `2.5` servings or `1.5` loaves are preserved instead of being rejected or truncated. `recipeYield` is now the **bare unit only** (e.g. `"cookies"`, `"cups"`, `"loaf"`) — Mealie renders it alongside `recipeYieldQuantity` as `"12 cookies"`. Callers that previously packed a full phrase into `recipeYield` (e.g. `"12 cookies"` or a per-serving sentence) should split the number into `recipeYieldQuantity` and leave only the unit in `recipeYield`.
- `src/tools/recipe_tools.py` — the `create_recipe` tool docstring now instructs the model to enter **per-serving** nutrition values (Mealie stores nutrition statically and never rescales it). Previously this guidance lived only in the guided-workflow prompt, so a direct `create_recipe` call could enter whole-recipe totals.

### Added

- `tests/test_mcp_server.py` — regression coverage that creates a recipe with fractional `recipeServings` (2.5) and `recipeYieldQuantity` (1.5) and asserts the fractions survive a create → `get_recipe_detailed` round-trip.

---

## [1.0.19] — 2026-07-21

### Security

- `src/auth.py` — hardened Authentik JWT verification (backported from the memory-vault project):
  - **Algorithm pinning.** `jwt.decode()` is now called with an explicit `algorithms=["RS256"]` allowlist. Previously joserfc validated against its default registry, leaving the door open to an algorithm-confusion attack (a token forged with `alg:HS256` using the RSA public-key bytes as the HMAC secret). Authentik signs OIDC tokens with RS256 when a Signing Key is configured (its default), so RS256 is pinned. If Authentik is switched to an EC signing certificate this allowlist must be updated to match.
  - **Signing-key rotation.** When a token's `kid` is absent from the cached JWKS, Authentik has likely rotated its signing key. The verifier now forces one immediate JWKS refetch instead of waiting out the hour-long cache TTL (which would otherwise fail every token for up to an hour after a rotation). The forced refetch is rate-limited to at most once per 60 seconds so a flood of bogus-`kid` tokens can't stampede Authentik.
  - **Single-flight fetches.** Discovery and JWKS fetches are guarded by `asyncio.Lock`, so a burst of concurrent token verifications on a cold cache no longer fires N simultaneous requests at Authentik. Warm-cache reads return before taking the lock, keeping the hot path contention-free.

### Changed (BREAKING)

- `src/auth.py` — `AUTHENTIK_AUDIENCE` is now **required** whenever authentication is enabled (whenever `AUTHENTIK_ISSUER` is set). The server fails closed at startup with a clear error if it is missing. Without an audience check the `aud` claim is not validated and *any* valid token from the issuer is accepted — including one minted for a different application that shares the same Authentik (a confused-deputy vulnerability). **Action required:** set `AUTHENTIK_AUDIENCE` to your provider's Client ID before upgrading any deployment that has auth enabled, or the server will not start. Deployments with auth disabled (`AUTHENTIK_ISSUER` unset) are unaffected.

### Added

- `tests/test_auth.py` — unit tests for the token verifier (audience accept/reject, RS256 algorithm pinning, `kid` rotation refetch + rate-limit, and `exp`/`nbf`/`iss` claim validation). Uses locally-minted RS256 keys and a stubbed JWKS — no live Authentik required.

---

## [1.0.18] — 2026-05-28

### Fixed

- `src/mealie/client.py` — `_handle_request` now catches `httpx.RemoteProtocolError` and retries the request once with a fresh connection. When the MCP server sits idle during a long OAuth setup flow, the persistent `httpx.Client` connection pool holds a TCP connection that Mealie (or the network) has already closed. The first tool call after the idle period would hit that stale connection, get a connection-reset error, and surface as a generic MCP error with no detail. The retry opens a fresh connection and succeeds. Without this fix, the very first tool call of a new session would fail roughly every time there was a delay between server startup and the first use.

---

## [1.0.17] — 2026-05-28

### Fixed

- `src/server.py` — `_internal_discovery_url()` now sends `X-Forwarded-Proto: https` when fetching the OIDC discovery document from the internal Docker URL. Without this header, Authentik generated all URLs in the discovery document with `http://` scheme (matching the internal HTTP fetch), causing ChatGPT to receive `http://` authorization and token endpoint URLs that would fail or mismatch the `https://` issuer claim in issued tokens.

---

## [1.0.16] — 2026-05-28

### Fixed

- `src/server.py` — `/.well-known/oauth-authorization-server` and `/.well-known/openid-configuration` now fetch the OIDC discovery document via the internal Docker URL when `AUTHENTIK_JWKS_URI` is set, instead of going through the external Cloudflare-proxied hostname. Cloudflare was returning 403 on container-to-container requests after a restart cleared the in-memory cache, causing a 500 on every reconnect attempt. The discovery URL is derived from `AUTHENTIK_JWKS_URI` by replacing `/jwks/` with `/.well-known/openid-configuration`; the `Host` header is set from `AUTHENTIK_HOST` so Authentik identifies the request correctly. The cached response still contains external URLs (token endpoint, authorization endpoint) so MCP clients can reach them.

---

## [1.0.15] — 2026-05-28

### Fixed

- `src/tools/tags_tools.py` and `src/tools/categories_tools.py` — recipe trimming guard changed from `if "recipes" in result:` to `if result.get("recipes"):`. Mealie returns `"recipes": null` for tags/categories with no assigned recipes; the old guard let `None` through, causing `TypeError: 'NoneType' is not iterable` on the list comprehension.

### Cleanup

- `tests/test_mcp_server.py` — removed all remaining orphaned `import re` and `import json, re` inline statements; `_re` and `_json` are now the sole imports used throughout `run()`.

---

## [1.0.14] — 2026-05-28

### Changed

- `tests/LLM_PROMPT.md` — added note explaining that ChatGPT may block `get_tag`, `get_tag_by_slug`, and `get_shopping_lists` via its safety filter and that this is a platform false positive, not a server error.

### Cleanup

- `tests/test_mcp_server.py` — removed all redundant inline `import re` and `import json` statements; updated all `re.findall` calls to `_re.findall` to use the aliases hoisted at the top of `run()` in v1.0.13.

---

## [1.0.13] — 2026-05-28

### Tests

- `tests/test_mcp_server.py` — `_json` and `_re` hoisted to top of `run()`. Previously `_json` was imported inside the `if state.get("category_id"):` guard, making it undefined for the category_slug, tag_id, and tag_slug blocks if no category ID was found in the instance.

---

## [1.0.12] — 2026-05-28

### Changed

- `USAGE_EXAMPLES.md` — `get_category`, `get_category_by_slug`, `get_tag`, `get_tag_by_slug` descriptions updated to state the `recipes` field contains slugs, not full recipe objects.

### Tests

- `tests/test_mcp_server.py` — `get_category`, `get_category_by_slug`, `get_tag`, `get_tag_by_slug` each assert that the `recipes` field in the response contains strings (slugs), not dicts — catches regression if the trimming is removed.

---

## [1.0.11] — 2026-05-28

### Fixed

- `src/tools/tags_tools.py` — `get_tag` and `get_tag_by_slug` now trim the embedded `recipes` array from full recipe objects down to a list of slugs before returning. Mealie embeds every full recipe in the tag response; for a tag like `my-recipes` this was 39 full objects, producing a payload large enough to trigger OpenAI's safety filter and block the tool call.
- `src/tools/categories_tools.py` — `get_category` and `get_category_by_slug` receive the same fix for the same reason.

### Changed

- `tests/LLM_PROMPT.md` — `get_shopping_lists`, `get_tags`, `get_tag`, and `get_tag_by_slug` moved to the top of the tool list so they are called early in the session before conversation context accumulates, reducing false-positive safety filter triggers.

---

## [1.0.10] — 2026-05-28

### Fixed

- `src/models/recipe.py` — `recipeCategory`, `tags`, and `tools` in the `Recipe` read model changed from `List[str]` to `List[Any]`. Mealie returns these as full objects (id/name/slug dicts), not plain strings; the wrong type caused `get_recipe_concise` to throw a Pydantic validation error on any recipe with categories, tags, or tools assigned.
- `src/tools/categories_tools.py` — `get_empty_categories()` return type corrected from `Dict[str, Any]` to `List[Dict[str, Any]]`. Mealie returns a list; the wrong annotation caused MCP to serialize the response incorrectly.
- `src/tools/tags_tools.py` — `get_empty_tags()` return type corrected from `Dict[str, Any]` to `List[Dict[str, Any]]`. Same issue as `get_empty_categories`.
- `src/mealie/categories.py` and `src/mealie/tags.py` — `get_empty_categories()` and `get_empty_tags()` fetcher-level return annotations corrected from `Dict[str, Any]` to `List[Dict[str, Any]]` to match the actual API response.

### Tests

- `tests/test_mcp_server.py` — pre-flight section now fetches a real category slug, tag slug, and tool slug and assigns them to the test recipe before calling `get_recipe_concise`. This exercises the `recipeCategory`/`tags`/`tools` fields with actual objects so the `List[Any]` validation is always exercised, not vacuously passed via empty lists.
- `tests/test_mcp_server.py` — `get_empty_categories` and `get_empty_tags` each get an explicit `isError` assertion to catch regression if the `List[Dict]` annotation reverts to `Dict`.

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
