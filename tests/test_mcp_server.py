"""
Script 2: MCP server end-to-end tests.

Connects to the running MCP server at /mcp and tests every registered tool
via the MCP protocol. Verifies tool registration, schema validation, and the
full FastMCP request/response cycle.

Requires the MCP server to be running in Docker before executing:
    docker compose -f tests/docker-compose.yml up -d --build
    python tests/test_mcp_server.py

Usage:
    cd mealie-mcp-server
    cp tests/.env.testing.template tests/.env.testing
    # edit tests/.env.testing with your values
    docker compose -f tests/docker-compose.yml up -d --build
    python tests/test_mcp_server.py
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.testing"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mealie import MealieFetcher

_mealie = MealieFetcher(
    base_url=os.environ["MEALIE_BASE_URL"],
    api_key=os.environ["MEALIE_API_KEY"],
)

log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)

try:
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession
except ImportError:
    print("ERROR: mcp package not found. Install with: pip install mcp")
    sys.exit(1)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, condition, detail))


def error_text(r) -> str:
    """Text of a tool result, for reporting why a call failed."""
    return " ".join(getattr(c, "text", "") for c in (r.content or []))[:300]


def check_tool(name: str, r) -> None:
    """Pass only if the tool call succeeded. A failing tool raises ToolError, which
    the MCP client returns as a normal result with isError=True and the error text
    as content — so checking that content is present would pass on failures too."""
    check(name, not r.isError, error_text(r) if r.isError else "")


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


EXPECTED_TOOLS = {
    # Recipes
    "get_recipes", "get_recipe_detailed", "get_recipe_concise",
    "create_recipe", "duplicate_recipe",
    "mark_recipe_last_made",
    "get_recipe_comments", "create_recipe_comment",
    "get_recipe_timeline",
    "get_recipe_share_tokens", "create_recipe_share_token",
    "get_recipe_exports",
    # Categories
    "get_categories", "get_category", "get_category_by_slug", "get_empty_categories",
    # Tags
    "get_tags", "get_tag", "get_tag_by_slug", "get_empty_tags",
    # Foods
    "get_foods", "get_food",
    "create_food", "merge_foods",
    # Organizers
    "get_cooking_tools", "get_units", "get_labels",
    # Cookbooks
    "get_cookbooks",
    # Shopping lists
    "get_shopping_lists", "create_shopping_list", "get_shopping_list",
    "update_shopping_list", "delete_shopping_list",
    "update_shopping_list_label_settings",
    "add_recipe_to_shopping_list", "remove_recipe_from_shopping_list",
    "add_recipes_to_shopping_list_bulk",
    "get_shopping_list_items", "get_shopping_list_item",
    "create_shopping_list_item", "create_shopping_list_items_bulk",
    "update_shopping_list_item", "update_shopping_list_items_bulk",
    "delete_shopping_list_item", "delete_shopping_list_items_bulk",
    # Meal plans
    "get_all_mealplans", "get_todays_mealplan",
    "create_mealplan", "create_mealplan_bulk",
    "update_mealplan", "delete_mealplan",
}


async def run(session: ClientSession) -> None:
    import json as _json
    import re as _re
    state: dict = {}

    # -----------------------------------------------------------------------
    section("Pre-test cleanup — remove stale test artifacts")
    # -----------------------------------------------------------------------
    for slug in ["test-recipe-copy", "test-recipe", "test-recipe-auto-food", "test-recipe-fractional", "test-recipe-unknown-unit"]:
        try:
            _mealie.delete_recipe(slug)
            print(f"  [cleanup] deleted stale recipe: {slug}")
        except Exception:
            pass

    try:
        foods = _mealie.get_foods(search="__test_food", per_page=50)
        for f in foods.get("items", []):
            if f.get("name", "").startswith("__test_"):
                try:
                    _mealie.delete_food(f["id"])
                    print(f"  [cleanup] deleted stale food: {f['name']}")
                except Exception:
                    pass
    except Exception:
        pass

    # -----------------------------------------------------------------------
    section("Tool registration")
    # -----------------------------------------------------------------------
    tools_response = await session.list_tools()
    registered = {t.name for t in tools_response.tools}

    check("tool count >= 51", len(registered) >= 51, f"got {len(registered)}")

    missing = EXPECTED_TOOLS - registered
    extra = registered - EXPECTED_TOOLS
    check("all expected tools registered", not missing, f"missing: {missing}" if missing else "")
    if extra:
        print(f"  [info] Extra tools registered (not in expected set): {extra}")

    # -----------------------------------------------------------------------
    section("Recipes — read")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_recipes", {"per_page": 5})
        data = r.content[0].text if r.content else "{}"
        check("get_recipes", "items" in data or "slug" in data)
    except Exception as e:
        check("get_recipes", False, str(e))

    # -----------------------------------------------------------------------
    section("Pre-flight — fetch organizer slugs for recipe creation test")
    # -----------------------------------------------------------------------
    for _fetch_tool, _key, _args in [
        ("get_categories",    "pre_category_slug", {"per_page": 5}),
        ("get_tags",          "pre_tag_slug",       {"per_page": 5}),
        ("get_cooking_tools", "pre_tool_slug",       {}),
    ]:
        try:
            _r = await session.call_tool(_fetch_tool, _args)
            _text = _r.content[0].text if _r.content else ""
            _slugs = _re.findall(r'"slug":\s*"([^"]+)"', _text)
            if _slugs:
                state[_key] = _slugs[0]
                print(f"  [info] {_key} = {_slugs[0]}")
        except Exception:
            pass

    # -----------------------------------------------------------------------
    section("Recipes — create and inspect")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {
                "name": "__test_recipe__",
                "description": "Automated test recipe — safe to delete",
                "tags": [state["pre_tag_slug"]] if state.get("pre_tag_slug") else [],
                "recipeCategory": [state["pre_category_slug"]] if state.get("pre_category_slug") else [],
                "tools": [state["pre_tool_slug"]] if state.get("pre_tool_slug") else [],
                "recipeIngredient": [],
                "recipeInstructions": [{"text": "Test step 1"}, {"text": "Test step 2"}],
                "recipeYield": "servings (1 serving per serving)",
                "recipeServings": 2,
                "recipeYieldQuantity": 2,
                "prepTime": "10 minutes",
                "performTime": "20 minutes",
                "totalTime": "30 minutes",
            }
        })
        text = r.content[0].text if r.content else ""
        check("create_recipe", "test" in text.lower() or len(text) > 10, text[:80])
        if "test-recipe" in text:
            state["recipe_slug"] = "test-recipe"
    except Exception as e:
        check("create_recipe", False, str(e))

    # Fall back to known slug if we created it
    if not state.get("recipe_slug"):
        state["recipe_slug"] = "test-recipe"

    slug = state["recipe_slug"]

    # Verify create_recipe auto-creates foods not in the catalog
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {
                "name": "__test_recipe_auto_food__",
                "description": "Auto-food creation test — safe to delete",
                "tags": [],
                "recipeCategory": [],
                "tools": [],
                "recipeIngredient": [
                    {"food": "__test_auto_food__", "quantity": 1.0, "disableAmount": False}
                ],
                "recipeInstructions": [{"text": "Test step"}],
                "recipeYield": "1 serving",
            }
        })
        text = r.content[0].text if r.content else ""
        check("create_recipe auto-creates unknown food", not r.isError and len(text) > 10, text[:80])
        if not r.isError:
            state["auto_food_recipe_slug"] = "test-recipe-auto-food"
        # Verify the food was created in the catalog
        foods = _mealie.get_foods(search="__test_auto_food__", per_page=10)
        auto_food = next((f for f in foods.get("items", []) if f.get("name") == "__test_auto_food__"), None)
        check("auto-created food exists in catalog", auto_food is not None)
        if auto_food:
            state["auto_food_id"] = auto_food["id"]
    except Exception as e:
        check("create_recipe auto-creates unknown food", False, str(e))

    # Verify fractional servings/yield round-trip as floats (recipeServings and
    # recipeYieldQuantity are float-typed; ints alone wouldn't exercise the change)
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {
                "name": "__test_recipe_fractional__",
                "description": "Fractional servings/yield test — safe to delete",
                "tags": [],
                "recipeCategory": [],
                "tools": [],
                "recipeIngredient": [],
                "recipeInstructions": [{"text": "Test step"}],
                "recipeServings": 2.5,
                "recipeYieldQuantity": 1.5,
                "recipeYield": "loaves",
            }
        })
        text = r.content[0].text if r.content else ""
        check("create_recipe accepts fractional servings/yield", not r.isError and len(text) > 10, text[:80])
        # Read it back and confirm the fractions survived the round-trip (not truncated to int)
        detailed = await session.call_tool("get_recipe_detailed", {"slug": "test-recipe-fractional"})
        dtext = detailed.content[0].text if detailed.content else ""
        check("fractional recipeServings round-trips (2.5)", "2.5" in dtext, dtext[:120])
        check("fractional recipeYieldQuantity round-trips (1.5)", "1.5" in dtext, dtext[:120])
    except Exception as e:
        check("create_recipe accepts fractional servings/yield", False, str(e))

    # Verify an unmatched ingredient unit is preserved in the note (not dropped).
    # Uses a unit name that cannot exist in the catalog so resolution always misses.
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {
                "name": "__test_recipe_unknown_unit__",
                "description": "Unknown-unit preservation test — safe to delete",
                "tags": [],
                "recipeCategory": [],
                "tools": [],
                "recipeIngredient": [
                    # no existing note → note becomes just the unit text
                    {"food": "__test_food_uu_a__", "quantity": 2.0,
                     "unit": "__test_unknown_unit__", "disableAmount": False},
                    # existing note → unit text is appended after it
                    {"food": "__test_food_uu_b__", "quantity": 3.0,
                     "unit": "__test_unknown_unit__", "note": "chopped",
                     "disableAmount": False},
                ],
                "recipeInstructions": [{"text": "Test step"}],
                "recipeYield": "1 serving",
            }
        })
        text = r.content[0].text if r.content else ""
        check("create_recipe accepts unknown unit", not r.isError and len(text) > 10, text[:80])
        state["unknown_unit_recipe_slug"] = "test-recipe-unknown-unit"

        detailed = await session.call_tool("get_recipe_detailed", {"slug": "test-recipe-unknown-unit"})
        dtext = detailed.content[0].text if detailed.content else ""
        # Pull the ingredient notes; parse JSON when possible, else fall back to substring.
        notes = []
        try:
            ings = _json.loads(dtext).get("recipeIngredient", [])
            notes = [i.get("note") or "" for i in ings]
        except Exception:
            notes = []
        if notes:
            check("unknown unit preserved in note (no prior note)",
                  any(n.strip() == "__test_unknown_unit__" for n in notes),
                  f"notes={notes}")
            check("unknown unit appended to existing note",
                  any("chopped" in n and "__test_unknown_unit__" in n for n in notes),
                  f"notes={notes}")
            check("unmatched unit not stored as structured unit",
                  all("__test_unknown_unit__" not in _json.dumps(i.get("unit"))
                      for i in _json.loads(dtext).get("recipeIngredient", [])),
                  "unknown unit leaked into the structured unit field")
        else:
            # Couldn't parse structured ingredients — assert the text at least survived
            check("unknown unit text preserved somewhere in recipe",
                  "__test_unknown_unit__" in dtext, dtext[:120])

        # Ingredient ids must be stored: Mealie makes up a new random one on every read
        # for an ingredient saved without one, so the create response and two reads
        # would all disagree
        reread = await session.call_tool("get_recipe_detailed", {"slug": "test-recipe-unknown-unit"})
        created_refs = [i.get("referenceId") for i in _json.loads(text).get("recipeIngredient", [])]
        read_refs = [i.get("referenceId") for i in _json.loads(dtext).get("recipeIngredient", [])]
        reread_refs = [i.get("referenceId") for i in _json.loads(reread.content[0].text).get("recipeIngredient", [])]
        check("create_recipe ingredient referenceIds are stored (create and two reads agree)",
              bool(read_refs) and created_refs == read_refs == reread_refs,
              f"created={created_refs} read={read_refs} reread={reread_refs}")
    except Exception as e:
        check("create_recipe accepts unknown unit", False, str(e))

    try:
        r = await session.call_tool("get_recipe_detailed", {"slug": slug})
        text = r.content[0].text if r.content else ""
        check("get_recipe_detailed", slug in text or "name" in text)
    except Exception as e:
        check("get_recipe_detailed", False, str(e))

    try:
        r = await session.call_tool("get_recipe_concise", {"slug": slug})
        text = r.content[0].text if r.content else ""
        check("get_recipe_concise", len(text) > 5)
        check("get_recipe_concise includes totalTime", "totalTime" in text, text[:80])
    except Exception as e:
        check("get_recipe_concise", False, str(e))
        check("get_recipe_concise includes totalTime", False, str(e))

    # Recipe times: create_recipe stores Mealie's structured seconds (not the legacy
    # text), and the read tools turn them back into readable text.
    try:
        raw = _mealie.get_recipe(slug)
        check("create_recipe stores times as seconds",
              (raw.get("prepTimeSeconds"), raw.get("performTimeSeconds"), raw.get("totalTimeSeconds"))
              == (600, 1200, 1800),
              str({k: raw.get(k) for k in ("prepTimeSeconds", "performTimeSeconds", "totalTimeSeconds")}))
        check("create_recipe leaves legacy time text empty",
              not (raw.get("prepTime") or raw.get("performTime") or raw.get("totalTime")),
              str({k: raw.get(k) for k in ("prepTime", "performTime", "totalTime")}))
        r = await session.call_tool("get_recipe_detailed", {"slug": slug})
        d = _json.loads(r.content[0].text)
        check("get_recipe_detailed readable times + seconds",
              (d.get("prepTime"), d.get("performTime"), d.get("totalTime"), d.get("totalTimeSeconds"))
              == ("10 minutes", "20 minutes", "30 minutes", 1800),
              str({k: d.get(k) for k in ("prepTime", "performTime", "totalTime", "totalTimeSeconds")}))
        check("get_recipe_detailed has lastMade key", "lastMade" in d)
        r = await session.call_tool("get_recipe_concise", {"slug": slug})
        c = _json.loads(r.content[0].text)
        check("get_recipe_concise totalTime is readable", c.get("totalTime") == "30 minutes", str(c.get("totalTime")))
        r = await session.call_tool("get_recipes", {"search": "__test_recipe__", "per_page": 10})
        items = [i for i in _json.loads(r.content[0].text).get("items", []) if i.get("slug") == slug]
        check("get_recipes list has readable times + seconds",
              bool(items) and items[0].get("totalTime") == "30 minutes" and items[0].get("totalTimeSeconds") == 1800,
              str({k: items[0].get(k) for k in ("totalTime", "totalTimeSeconds")}) if items else "recipe not in list")
    except Exception as e:
        check("recipe time round-trip", False, str(e))

    # A unit-less time is rejected before anything is created
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {"name": "__test_recipe_bare_time__", "prepTime": "45"}
        })
        check("create_recipe rejects bare-number time",
              r.isError and "no unit" in error_text(r), error_text(r))
        try:
            _mealie.get_recipe("test-recipe-bare-time")
            check("bare-number rejection created no recipe", False, "stub recipe exists — deleting it")
            _mealie.delete_recipe("test-recipe-bare-time")
        except Exception:
            check("bare-number rejection created no recipe", True)
    except Exception as e:
        check("create_recipe rejects bare-number time", False, str(e))

    check(
        "get_recipe_concise exercised recipeCategory/tags/tools (organizers populated)",
        bool(state.get("pre_category_slug") or state.get("pre_tag_slug") or state.get("pre_tool_slug")),
        "no organizers found in instance — List[Any] validation not exercised" if not (
            state.get("pre_category_slug") or state.get("pre_tag_slug") or state.get("pre_tool_slug")
        ) else "",
    )

    try:
        r = await session.call_tool("duplicate_recipe", {"slug": slug, "name": "__test_recipe_copy__"})
        text = r.content[0].text if r.content else ""
        check("duplicate_recipe", len(text) > 5)
        if "test-recipe-copy" in text:
            state["recipe_copy_slug"] = "test-recipe-copy"
        if not r.isError:
            dup = _json.loads(text)
            check("duplicate_recipe copies seconds and shows readable times",
                  (dup.get("totalTime"), dup.get("totalTimeSeconds")) == ("30 minutes", 1800),
                  str({k: dup.get(k) for k in ("totalTime", "totalTimeSeconds")}))
    except Exception as e:
        check("duplicate_recipe", False, str(e))

    try:
        r = await session.call_tool("mark_recipe_last_made", {"slug": slug})
        check_tool("mark_recipe_last_made", r)
    except Exception as e:
        check("mark_recipe_last_made", False, str(e))

    # Mealie v3.29+ keeps lastMade per household, not on the recipe; the read tools add it back
    try:
        r = await session.call_tool("get_recipe_concise", {"slug": slug})
        c = _json.loads(r.content[0].text)
        check("get_recipe_concise shows lastMade after mark_recipe_last_made",
              bool(c.get("lastMade")), str(c.get("lastMade")))
    except Exception as e:
        check("get_recipe_concise shows lastMade after mark_recipe_last_made", False, str(e))

    try:
        r = await session.call_tool("get_recipe_comments", {"slug": slug})
        check_tool("get_recipe_comments", r)
    except Exception as e:
        check("get_recipe_comments", False, str(e))

    try:
        r = await session.call_tool("create_recipe_comment", {"slug": slug, "text": "MCP test comment"})
        check_tool("create_recipe_comment", r)
    except Exception as e:
        check("create_recipe_comment", False, str(e))

    try:
        r = await session.call_tool("get_recipe_timeline", {"per_page": 5})
        text = r.content[0].text if r.content else ""
        check("get_recipe_timeline", "items" in text or len(text) > 5)
    except Exception as e:
        check("get_recipe_timeline", False, str(e))

    try:
        r = await session.call_tool("get_recipe_share_tokens", {"slug": slug})
        check_tool("get_recipe_share_tokens", r)
    except Exception as e:
        check("get_recipe_share_tokens", False, str(e))

    try:
        r = await session.call_tool("create_recipe_share_token", {"slug": slug})
        check_tool("create_recipe_share_token", r)
    except Exception as e:
        check("create_recipe_share_token", False, str(e))

    try:
        r = await session.call_tool("get_recipe_exports", {"slug": slug})
        check_tool("get_recipe_exports", r)
    except Exception as e:
        check("get_recipe_exports", False, str(e))

    # -----------------------------------------------------------------------
    section("Categories")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_categories", {"per_page": 5})
        check_tool("get_categories", r)
    except Exception as e:
        check("get_categories", False, str(e))

    try:
        r = await session.call_tool("get_empty_categories", {})
        check_tool("get_empty_categories", r)
        # FastMCP creates one TextContent item per list element, so isError=False means
        # the List[Dict] annotation matched — catches regression if annotation reverts to Dict
        check("get_empty_categories returns list", not r.isError, r.content[0].text[:60] if r.isError and r.content else "")
    except Exception as e:
        check("get_empty_categories", False, str(e))
        check("get_empty_categories returns list", False, str(e))

    try:
        r = await session.call_tool("get_categories", {"per_page": 5})
        text = r.content[0].text if r.content else ""
        if '"id"' in text:
            ids = _re.findall(r'"id":\s*"([^"]+)"', text)
            slugs = _re.findall(r'"slug":\s*"([^"]+)"', text)
            if ids:
                state["category_id"] = ids[0]
            if slugs:
                state["category_slug"] = slugs[0]
    except Exception:
        pass

    if state.get("category_id"):
        try:
            r = await session.call_tool("get_category", {"category_id": state["category_id"]})
            check_tool("get_category", r)
            _data = _json.loads(r.content[0].text) if r.content else {}
            _recipes = _data.get("recipes", [])
            check("get_category recipes are slugs", not _recipes or isinstance(_recipes[0], str),
                  str(_recipes[0])[:60] if _recipes else "empty")
        except Exception as e:
            check("get_category", False, str(e))
            check("get_category recipes are slugs", False, str(e))

    if state.get("category_slug"):
        try:
            r = await session.call_tool("get_category_by_slug", {"category_slug": state["category_slug"]})
            check_tool("get_category_by_slug", r)
            _data = _json.loads(r.content[0].text) if r.content else {}
            _recipes = _data.get("recipes", [])
            check("get_category_by_slug recipes are slugs", not _recipes or isinstance(_recipes[0], str),
                  str(_recipes[0])[:60] if _recipes else "empty")
        except Exception as e:
            check("get_category_by_slug", False, str(e))
            check("get_category_by_slug recipes are slugs", False, str(e))

    # -----------------------------------------------------------------------
    section("Tags")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_tags", {"per_page": 5})
        check_tool("get_tags", r)
    except Exception as e:
        check("get_tags", False, str(e))

    try:
        r = await session.call_tool("get_empty_tags", {})
        check_tool("get_empty_tags", r)
        check("get_empty_tags returns list", not r.isError, r.content[0].text[:60] if r.isError and r.content else "")
    except Exception as e:
        check("get_empty_tags", False, str(e))
        check("get_empty_tags returns list", False, str(e))

    try:
        r = await session.call_tool("get_tags", {"per_page": 5})
        text = r.content[0].text if r.content else ""
        ids = _re.findall(r'"id":\s*"([^"]+)"', text)
        slugs = _re.findall(r'"slug":\s*"([^"]+)"', text)
        if ids:
            state["tag_id"] = ids[0]
        if slugs:
            state["tag_slug"] = slugs[0]
    except Exception:
        pass

    if state.get("tag_id"):
        try:
            r = await session.call_tool("get_tag", {"tag_id": state["tag_id"]})
            check_tool("get_tag", r)
            _data = _json.loads(r.content[0].text) if r.content else {}
            _recipes = _data.get("recipes", [])
            check("get_tag recipes are slugs", not _recipes or isinstance(_recipes[0], str),
                  str(_recipes[0])[:60] if _recipes else "empty")
        except Exception as e:
            check("get_tag", False, str(e))
            check("get_tag recipes are slugs", False, str(e))

    if state.get("tag_slug"):
        try:
            r = await session.call_tool("get_tag_by_slug", {"tag_slug": state["tag_slug"]})
            check_tool("get_tag_by_slug", r)
            _data = _json.loads(r.content[0].text) if r.content else {}
            _recipes = _data.get("recipes", [])
            check("get_tag_by_slug recipes are slugs", not _recipes or isinstance(_recipes[0], str),
                  str(_recipes[0])[:60] if _recipes else "empty")
        except Exception as e:
            check("get_tag_by_slug", False, str(e))
            check("get_tag_by_slug recipes are slugs", False, str(e))

    # -----------------------------------------------------------------------
    section("Foods")
    # -----------------------------------------------------------------------
    for tool, args in [
        ("get_foods", {"per_page": 5}),
    ]:
        try:
            r = await session.call_tool(tool, args)
            check_tool(tool, r)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("create_food", {"name": "__test_food_a__"})
        text = r.content[0].text if r.content else ""
        check("create_food (__test_food_a__)", "__test_food_a__" in text or "id" in text)
        ids = _re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["food_a_id"] = ids[0]
    except Exception as e:
        check("create_food (__test_food_a__)", False, str(e))

    try:
        r = await session.call_tool("create_food", {"name": "__test_food_b__"})
        text = r.content[0].text if r.content else ""
        check("create_food (__test_food_b__)", "__test_food_b__" in text or "id" in text)
        ids = _re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["food_b_id"] = ids[0]
    except Exception as e:
        check("create_food (__test_food_b__)", False, str(e))

    if state.get("food_a_id"):
        try:
            r = await session.call_tool("get_food", {"item_id": state["food_a_id"]})
            check_tool("get_food", r)
        except Exception as e:
            check("get_food", False, str(e))

    if state.get("food_a_id") and state.get("food_b_id"):
        try:
            r = await session.call_tool("merge_foods", {
                "from_food_id": state["food_b_id"],
                "to_food_id": state["food_a_id"],
            })
            check_tool("merge_foods", r)
            state["food_b_id"] = None
        except Exception as e:
            check("merge_foods", False, str(e))

    # -----------------------------------------------------------------------
    section("Organizers")
    # -----------------------------------------------------------------------
    for tool in ["get_cooking_tools", "get_units", "get_labels"]:
        try:
            r = await session.call_tool(tool, {})
            check_tool(tool, r)
        except Exception as e:
            check(tool, False, str(e))

    # -----------------------------------------------------------------------
    section("Household — Cookbooks")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_cookbooks", {})
        check_tool("get_cookbooks", r)
    except Exception as e:
        check("get_cookbooks", False, str(e))

    # -----------------------------------------------------------------------
    section("Shopping Lists")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_shopping_lists", {})
        check_tool("get_shopping_lists", r)
    except Exception as e:
        check("get_shopping_lists", False, str(e))

    try:
        r = await session.call_tool("create_shopping_list", {"name": "__test_shopping_list__"})
        text = r.content[0].text if r.content else ""
        check("create_shopping_list", "id" in text)
        ids = _re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["shopping_list_id"] = ids[0]
    except Exception as e:
        check("create_shopping_list", False, str(e))

    if state.get("shopping_list_id"):
        lid = state["shopping_list_id"]

        for tool, args in [
            ("get_shopping_list", {"list_id": lid}),
            ("update_shopping_list", {"list_id": lid, "name": "__test_shopping_list_renamed__"}),
            ("get_shopping_list_items", {}),
        ]:
            try:
                r = await session.call_tool(tool, args)
                check_tool(tool, r)
            except Exception as e:
                check(tool, False, str(e))

        # Section order by label name: named labels first, the rest keep their order
        def label_order(list_data: dict) -> list:
            return [st["label"]["name"] for st in
                    sorted(list_data.get("labelSettings", []), key=lambda st: st["position"])]

        try:
            before = label_order(_mealie.get_shopping_list(lid))
            if len(before) >= 3:
                pick = [before[-1], before[-2], before[-3]]
                r = await session.call_tool("update_shopping_list_label_settings", {
                    "list_id": lid, "labels": [pick[0].upper(), pick[1], pick[2]],
                })
                out = _json.loads(r.content[0].text) if not r.isError else {}
                expected = pick + [n for n in before if n not in pick]
                check("update_shopping_list_label_settings orders named labels first, rest unchanged",
                      out.get("labelOrder") == expected and label_order(_mealie.get_shopping_list(lid)) == expected,
                      error_text(r) if r.isError else str(out.get("labelOrder", ""))[:120])

                r = await session.call_tool("update_shopping_list_label_settings", {
                    "list_id": lid, "labels": [before[0], "__not_a_label__"],
                })
                msg = error_text(r)
                check("update_shopping_list_label_settings rejects an unknown name and lists the real ones",
                      r.isError and "__not_a_label__" in msg and before[1] in msg, msg[:160])
                check("unknown label name changes nothing",
                      label_order(_mealie.get_shopping_list(lid)) == expected)

                r = await session.call_tool("update_shopping_list_label_settings", {"list_id": lid, "labels": []})
                check("update_shopping_list_label_settings rejects an empty list", r.isError, error_text(r)[:120])
            else:
                check("update_shopping_list_label_settings", False, f"need 3+ labels, list has {len(before)}")
        except Exception as e:
            check("update_shopping_list_label_settings", False, str(e))

        try:
            r = await session.call_tool("create_shopping_list_item", {
                "shopping_list_id": lid, "note": "__test_item__"
            })
            text = r.content[0].text if r.content else ""
            check("create_shopping_list_item", "id" in text)
            ids = _re.findall(r'"id":\s*"([^"]+)"', text)
            if ids:
                state["shopping_item_id"] = ids[0]
        except Exception as e:
            check("create_shopping_list_item", False, str(e))

        if state.get("shopping_item_id"):
            iid = state["shopping_item_id"]

            for tool, args in [
                ("get_shopping_list_item", {"item_id": iid}),
                ("update_shopping_list_item", {"item_id": iid, "checked": True}),
                ("create_shopping_list_items_bulk", {
                    "items": [{"shoppingListId": lid, "note": "__test_bulk__", "checked": False}]
                }),
                ("update_shopping_list_items_bulk", {
                    "items": [{"id": iid, "shoppingListId": lid, "note": "__test_item__", "checked": False}]
                }),
                ("delete_shopping_list_item", {"item_id": iid}),
            ]:
                try:
                    r = await session.call_tool(tool, args)
                    check_tool(tool, r)
                except Exception as e:
                    check(tool, False, str(e))

        # Recipe integration — get recipe UUID for shopping list recipe tests
        try:
            r = await session.call_tool("get_recipe_detailed", {"slug": slug})
            text = r.content[0].text if r.content else ""
            ids = _re.findall(r'"id":\s*"([^"]+)"', text)
            if ids:
                state["recipe_id"] = ids[0]
        except Exception:
            pass

        if state.get("recipe_id"):
            rid = state["recipe_id"]
            for tool, args in [
                ("add_recipe_to_shopping_list", {"list_id": lid, "recipe_id": rid}),
                ("remove_recipe_from_shopping_list", {"list_id": lid, "recipe_id": rid}),
                ("add_recipes_to_shopping_list_bulk", {
                    "list_id": lid,
                    "recipes": [{"recipeId": rid, "recipeIncrementQuantity": 1}],
                }),
            ]:
                try:
                    r = await session.call_tool(tool, args)
                    check_tool(tool, r)
                except Exception as e:
                    check(tool, False, str(e))

            # Recipe references are trimmed to identify the recipe, not embed it
            try:
                r = await session.call_tool("get_shopping_list", {"list_id": lid})
                refs = _json.loads(r.content[0].text).get("recipeReferences", []) if not r.isError else []
                check("get_shopping_list recipeReferences trimmed to recipeId/name/slug/recipeQuantity",
                      bool(refs) and all(set(ref) == {"recipeId", "name", "slug", "recipeQuantity"}
                                         and ref["recipeId"] == rid and ref["slug"] == slug for ref in refs),
                      str(refs)[:200] if refs else error_text(r) or "no recipeReferences")
            except Exception as e:
                check("get_shopping_list recipeReferences trimmed to recipeId/name/slug/recipeQuantity",
                      False, str(e))

        try:
            r = await session.call_tool("delete_shopping_list_items_bulk", {
                "item_ids": []
            })
            # An empty list must be rejected: the tool raises ToolError, which comes
            # back as an isError result carrying the "cannot be empty" message
            check("delete_shopping_list_items_bulk rejects empty list",
                  r.isError and "cannot be empty" in error_text(r).lower(), error_text(r))
        except Exception as e:
            check("delete_shopping_list_items_bulk rejects empty list", False, str(e))

        try:
            r = await session.call_tool("delete_shopping_list", {"list_id": lid})
            check_tool("delete_shopping_list", r)
            state["shopping_list_id"] = None
        except Exception as e:
            check("delete_shopping_list", False, str(e))

    # -----------------------------------------------------------------------
    section("Meal Plans")
    # -----------------------------------------------------------------------
    for tool, args in [
        ("get_all_mealplans", {}),
        ("get_todays_mealplan", {}),
    ]:
        try:
            r = await session.call_tool(tool, args)
            check_tool(tool, r)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("create_mealplan_bulk", {
            "entries": [{"date": "2099-01-03", "entry_type": "lunch", "title": "__test_bulk_mealplan__"}]
        })
        check_tool("create_mealplan_bulk", r)
        created = _json.loads(r.content[0].text).get("created", []) if not r.isError else []
        check("create_mealplan_bulk returns the created entry with its id",
              len(created) == 1 and isinstance(created[0].get("id"), int)
              and created[0].get("title") == "__test_bulk_mealplan__" and "recipe" not in created[0],
              str(created)[:160])
    except Exception as e:
        check("create_mealplan_bulk", False, str(e))

    try:
        r = await session.call_tool("create_mealplan_bulk", {"entries": [
            {"date": "2099-01-04", "entry_type": "lunch", "title": "__test_bulk_rejected__"},
            {"date": "2099-01-05", "entry_type": "brunch", "title": "__test_bulk_rejected__"},
        ]})
        leftover = [e for e in _mealie.get_mealplans(start_date="2099-01-01", end_date="2099-01-31", per_page=-1)
                    .get("items", []) if e.get("title") == "__test_bulk_rejected__"]
        check("create_mealplan_bulk with one bad entry creates nothing",
              r.isError and "brunch" in error_text(r) and not leftover,
              error_text(r)[:160] + (f" — created {len(leftover)}" if leftover else ""))
    except Exception as e:
        check("create_mealplan_bulk with one bad entry creates nothing", False, str(e))

    try:
        r = await session.call_tool("create_mealplan", {
            "date": "2099-01-01", "entry_type": "dinner", "title": "__test_mealplan__"
        })
        text = r.content[0].text if r.content else ""
        check("create_mealplan", not r.isError and "id" in text, error_text(r) if r.isError else "")
        entry = _json.loads(text) if not r.isError else {}
        check("create_mealplan returns the trimmed entry",
              set(entry) == {"id", "date", "entryType", "title"} and entry.get("title") == "__test_mealplan__",
              str(entry)[:160])
        ids = _re.findall(r'"id":\s*(\d+)', text)
        if ids:
            state["mealplan_id"] = ids[0]
    except Exception as e:
        check("create_mealplan", False, str(e))

    if state.get("mealplan_id"):
        mid = state["mealplan_id"]
        try:
            # Meal plan ids are numbers; the tools take them as a number or as text
            r = await session.call_tool("update_mealplan", {
                "entry_id": int(mid), "date": "2099-01-02", "entry_type": "dinner"
            })
            check_tool("update_mealplan (numeric entry_id)", r)
            updated = _json.loads(r.content[0].text) if not r.isError else {}
            check("update_mealplan returns the trimmed entry",
                  set(updated) == {"id", "date", "entryType", "title"} and updated.get("date") == "2099-01-02",
                  str(updated))
        except Exception as e:
            check("update_mealplan (numeric entry_id)", False, str(e))

        try:
            r = await session.call_tool("delete_mealplan", {"entry_id": str(mid)})
            check_tool("delete_mealplan (text entry_id)", r)
            state["mealplan_id"] = None
        except Exception as e:
            check("delete_mealplan", False, str(e))

    # Whole-week entries (Mealie v3.30+): the week follows the household's
    # firstDayOfWeek (0=Sunday) and must end exactly six days after it starts.
    from datetime import date as _date, timedelta as _td
    first_day = _mealie.get_household_preferences().get("firstDayOfWeek") or 0

    def is_week_of(entry: dict, day: str) -> bool:
        start, d = _date.fromisoformat(entry["date"]), _date.fromisoformat(day)
        return ((start.weekday() + 1) % 7 == first_day and start <= d < start + _td(days=7)
                and entry.get("endDate") == (start + _td(days=6)).isoformat())

    def mealplans_between(start: str, end: str) -> list:
        r = _mealie.get_mealplans(start_date=start, end_date=end, per_page=-1)
        return r.get("items", [])

    try:
        r = await session.call_tool("create_mealplan", {
            "date": "2099-01-07", "entry_type": "dinner", "title": "__test_week_mealplan__",
            "whole_week": True,
        })
        week = _json.loads(r.content[0].text) if not r.isError else {}
        check("create_mealplan whole_week aligns to household week",
              bool(week) and is_week_of(week, "2099-01-07"),
              error_text(r) if r.isError else f"date={week.get('date')} endDate={week.get('endDate')}")
        wid = week.get("id")
        if wid:
            mid_week = (_date.fromisoformat(week["date"]) + _td(days=3)).isoformat()
            in_range = mealplans_between(mid_week, mid_week)
            check("get_all_mealplans includes overlapping week entry",
                  any(e["id"] == wid for e in in_range), f"ids={[e['id'] for e in in_range]}")
            leaked = any(e.get("title") == "__test_bulk_mealplan__" for e in in_range)
            check("get_all_mealplans date filter excludes entries outside the range", not leaked,
                  "2099-01-03 day entry returned for a later range" if leaked else "")
            r = await session.call_tool("get_all_mealplans", {"start_date": mid_week, "end_date": mid_week})
            check("get_all_mealplans tool returns week entry",
                  not r.isError and any(e["id"] == wid for e in _json.loads(r.content[0].text).get("items", [])),
                  error_text(r))

            r = await session.call_tool("update_mealplan", {
                "entry_id": str(wid), "date": "2099-01-21", "entry_type": "dinner",
            })
            moved = _json.loads(r.content[0].text) if not r.isError else {}
            check("update_mealplan moves week entry (end date follows)",
                  bool(moved) and is_week_of(moved, "2099-01-21"),
                  error_text(r) if r.isError else f"date={moved.get('date')} endDate={moved.get('endDate')}")
            r = await session.call_tool("update_mealplan", {
                "entry_id": str(wid), "date": "2099-01-21", "entry_type": "dinner", "whole_week": False,
            })
            day = _json.loads(r.content[0].text) if not r.isError else {}
            check("update_mealplan whole_week=False makes a day entry",
                  day.get("date") == "2099-01-21" and not day.get("endDate"),
                  error_text(r) if r.isError else f"date={day.get('date')} endDate={day.get('endDate')}")
            r = await session.call_tool("delete_mealplan", {"entry_id": wid})
            check_tool("delete_mealplan (week entry, numeric entry_id)", r)
    except Exception as e:
        check("whole-week meal plan entries", False, str(e))

    try:
        r = await session.call_tool("create_mealplan_bulk", {
            "entries": [{"date": "2099-02-04", "entry_type": "dinner",
                         "title": "__test_bulk_week_mealplan__", "whole_week": True}]
        })
        check_tool("create_mealplan_bulk (whole_week)", r)
        created = _json.loads(r.content[0].text).get("created", []) if not r.isError else []
        check("create_mealplan_bulk whole_week entry returned with its endDate",
              len(created) == 1 and bool(created[0].get("endDate")), str(created)[:160])
        bulk = [e for e in mealplans_between("2099-02-01", "2099-02-28")
                if e.get("title") == "__test_bulk_week_mealplan__"]
        check("create_mealplan_bulk whole_week entry aligns to household week",
              len(bulk) == 1 and is_week_of(bulk[0], "2099-02-04"), str(bulk))
    except Exception as e:
        check("create_mealplan_bulk (whole_week)", False, str(e))

    # -----------------------------------------------------------------------
    section("Cleanup — test recipes and foods")
    # -----------------------------------------------------------------------
    for slug in [
        state.get("recipe_copy_slug", "test-recipe-copy"),
        state.get("recipe_slug", "test-recipe"),
        state.get("auto_food_recipe_slug"),
        "test-recipe-fractional",
        state.get("unknown_unit_recipe_slug", "test-recipe-unknown-unit"),
    ]:
        if slug:
            try:
                r = _mealie.delete_recipe(slug)
                check(f"cleanup delete_recipe ({slug})", isinstance(r, dict))
            except Exception as e:
                check(f"cleanup delete_recipe ({slug})", False, str(e))

    if state.get("food_a_id"):
        try:
            r = _mealie.delete_food(state["food_a_id"])
            check(f"cleanup delete_food (food_a)", isinstance(r, dict))
        except Exception as e:
            check(f"cleanup delete_food (food_a)", False, str(e))

    if state.get("auto_food_id"):
        try:
            r = _mealie.delete_food(state["auto_food_id"])
            check(f"cleanup delete_food (__test_auto_food__)", isinstance(r, dict))
        except Exception as e:
            check(f"cleanup delete_food (__test_auto_food__)", False, str(e))

    # Sweep any remaining __test_ foods auto-created during recipe creation
    # (e.g. the __test_food_uu_* foods behind the unknown-unit recipe) so a
    # single run leaves nothing behind.
    try:
        leftover = _mealie.get_foods(search="__test_food", per_page=50)
        for f in leftover.get("items", []):
            if f.get("name", "").startswith("__test_"):
                try:
                    _mealie.delete_food(f["id"])
                    check(f"cleanup delete_food ({f['name']})", True)
                except Exception as e:
                    check(f"cleanup delete_food ({f['name']})", False, str(e))
    except Exception:
        pass

    # Sweep every __test_ meal plan by title. create_mealplan_bulk entries were
    # never captured for deletion, so without this they accumulate on the far-future
    # test dates run after run. Title-based so it also mops up any orphaned single
    # entry from a crashed run.
    try:
        mp = _mealie.get_mealplans(start_date="2098-01-01", end_date="2100-12-31", per_page=500)
        for entry in mp.get("items", []):
            if str(entry.get("title", "")).startswith("__test_"):
                try:
                    _mealie.delete_mealplan(str(entry["id"]))
                    check(f"cleanup delete_mealplan ({entry['title']} id={entry['id']})", True)
                except Exception as e:
                    check(f"cleanup delete_mealplan (id={entry['id']})", False, str(e))
    except Exception:
        pass

    # Sweep every __test_ shopping list by name, so a list orphaned by a crashed
    # run (delete-by-captured-id is skipped if the run dies mid-way) can't persist.
    try:
        sl = _mealie.get_shopping_lists(per_page=200)
        for lst in sl.get("items", []):
            if str(lst.get("name", "")).startswith("__test_"):
                try:
                    _mealie.delete_shopping_list(lst["id"])
                    check(f"cleanup delete_shopping_list ({lst['name']})", True)
                except Exception as e:
                    check(f"cleanup delete_shopping_list (id={lst['id']})", False, str(e))
    except Exception:
        pass

    # -----------------------------------------------------------------------
    section("Summary")
    # -----------------------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)
    print(f"\n  {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)\n\nFailed tests:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}" + (f": {detail}" if detail else ""))
    else:
        print(" — all tests passed")
    print()
    return failed


async def main() -> int:
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
    print(f"\nConnecting to MCP server at {mcp_url} ...")

    try:
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected.\n")
                return await run(session)
    except Exception as e:
        print(f"ERROR: Could not connect to MCP server — {e}")
        print("Is the server running? Try: docker compose -f tests/docker-compose.yml up -d --build")
        sys.exit(1)


if __name__ == "__main__":
    # Exit after main() returns: a SystemExit raised inside the MCP client's async
    # context managers is wrapped in a BaseExceptionGroup, so even a fully passing
    # run exited with code 1.
    sys.exit(0 if asyncio.run(main()) == 0 else 1)
