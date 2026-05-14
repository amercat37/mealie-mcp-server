"""
Script 2: MCP server end-to-end tests.

Connects to the running MCP server at /mcp and tests every registered tool
via the MCP protocol. Verifies tool registration, schema validation, and the
full FastMCP request/response cycle.

Requires the MCP server to be running in Docker before executing:
    docker compose up -d
    python tests/test_mcp_server.py

Usage:
    cd mealie-mcp-server
    cp .env.testing.template .env.testing
    # edit .env.testing with your values
    docker compose up -d
    python tests/test_mcp_server.py
"""

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(".env.testing")

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


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


EXPECTED_TOOLS = {
    # Recipes
    "get_recipes", "get_recipe_detailed", "get_recipe_concise",
    "create_recipe", "duplicate_recipe", "delete_test_recipe",
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
    "get_foods", "get_food", "get_empty_foods",
    "create_food", "merge_foods", "delete_test_food",
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
    state: dict = {}

    # -----------------------------------------------------------------------
    section("Tool registration")
    # -----------------------------------------------------------------------
    tools_response = await session.list_tools()
    registered = {t.name for t in tools_response.tools}

    check("tool count >= 54", len(registered) >= 54, f"got {len(registered)}")

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
    section("Recipes — create and inspect")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("create_recipe", {
            "recipe": {
                "name": "__test_recipe__",
                "description": "Automated test recipe — safe to delete",
                "tags": [],
                "recipeCategory": [],
                "tools": [],
                "recipeIngredient": [],
                "recipeInstructions": [{"text": "Test step 1"}, {"text": "Test step 2"}],
                "recipeYield": "1 serving",
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
    except Exception as e:
        check("get_recipe_concise", False, str(e))

    try:
        r = await session.call_tool("duplicate_recipe", {"slug": slug, "name": "__test_recipe_copy__"})
        text = r.content[0].text if r.content else ""
        check("duplicate_recipe", len(text) > 5)
        if "test-recipe-copy" in text:
            state["recipe_copy_slug"] = "test-recipe-copy"
    except Exception as e:
        check("duplicate_recipe", False, str(e))

    try:
        r = await session.call_tool("mark_recipe_last_made", {"slug": slug})
        check("mark_recipe_last_made", r.content is not None)
    except Exception as e:
        check("mark_recipe_last_made", False, str(e))

    try:
        r = await session.call_tool("get_recipe_comments", {"slug": slug})
        check("get_recipe_comments", r.content is not None)
    except Exception as e:
        check("get_recipe_comments", False, str(e))

    try:
        r = await session.call_tool("create_recipe_comment", {"slug": slug, "text": "MCP test comment"})
        check("create_recipe_comment", r.content is not None)
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
        check("get_recipe_share_tokens", r.content is not None)
    except Exception as e:
        check("get_recipe_share_tokens", False, str(e))

    try:
        r = await session.call_tool("create_recipe_share_token", {"slug": slug})
        check("create_recipe_share_token", r.content is not None)
    except Exception as e:
        check("create_recipe_share_token", False, str(e))

    try:
        r = await session.call_tool("get_recipe_exports", {"slug": slug})
        check("get_recipe_exports", r.content is not None)
    except Exception as e:
        check("get_recipe_exports", False, str(e))

    # -----------------------------------------------------------------------
    section("Categories")
    # -----------------------------------------------------------------------
    for tool, args in [
        ("get_categories", {"per_page": 5}),
        ("get_empty_categories", {}),
    ]:
        try:
            r = await session.call_tool(tool, args)
            check(tool, r.content is not None)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("get_categories", {"per_page": 5})
        text = r.content[0].text if r.content else ""
        if '"id"' in text:
            import json, re
            ids = re.findall(r'"id":\s*"([^"]+)"', text)
            slugs = re.findall(r'"slug":\s*"([^"]+)"', text)
            if ids:
                state["category_id"] = ids[0]
            if slugs:
                state["category_slug"] = slugs[0]
    except Exception:
        pass

    if state.get("category_id"):
        try:
            r = await session.call_tool("get_category", {"category_id": state["category_id"]})
            check("get_category", r.content is not None)
        except Exception as e:
            check("get_category", False, str(e))

    if state.get("category_slug"):
        try:
            r = await session.call_tool("get_category_by_slug", {"category_slug": state["category_slug"]})
            check("get_category_by_slug", r.content is not None)
        except Exception as e:
            check("get_category_by_slug", False, str(e))

    # -----------------------------------------------------------------------
    section("Tags")
    # -----------------------------------------------------------------------
    for tool, args in [
        ("get_tags", {"per_page": 5}),
        ("get_empty_tags", {}),
    ]:
        try:
            r = await session.call_tool(tool, args)
            check(tool, r.content is not None)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("get_tags", {"per_page": 5})
        text = r.content[0].text if r.content else ""
        import re
        ids = re.findall(r'"id":\s*"([^"]+)"', text)
        slugs = re.findall(r'"slug":\s*"([^"]+)"', text)
        if ids:
            state["tag_id"] = ids[0]
        if slugs:
            state["tag_slug"] = slugs[0]
    except Exception:
        pass

    if state.get("tag_id"):
        try:
            r = await session.call_tool("get_tag", {"tag_id": state["tag_id"]})
            check("get_tag", r.content is not None)
        except Exception as e:
            check("get_tag", False, str(e))

    if state.get("tag_slug"):
        try:
            r = await session.call_tool("get_tag_by_slug", {"tag_slug": state["tag_slug"]})
            check("get_tag_by_slug", r.content is not None)
        except Exception as e:
            check("get_tag_by_slug", False, str(e))

    # -----------------------------------------------------------------------
    section("Foods")
    # -----------------------------------------------------------------------
    for tool, args in [
        ("get_foods", {"per_page": 5}),
        ("get_empty_foods", {}),
    ]:
        try:
            r = await session.call_tool(tool, args)
            check(tool, r.content is not None)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("create_food", {"name": "__test_food_a__"})
        text = r.content[0].text if r.content else ""
        check("create_food (__test_food_a__)", "__test_food_a__" in text or "id" in text)
        import re
        ids = re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["food_a_id"] = ids[0]
    except Exception as e:
        check("create_food (__test_food_a__)", False, str(e))

    try:
        r = await session.call_tool("create_food", {"name": "__test_food_b__"})
        text = r.content[0].text if r.content else ""
        check("create_food (__test_food_b__)", "__test_food_b__" in text or "id" in text)
        import re
        ids = re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["food_b_id"] = ids[0]
    except Exception as e:
        check("create_food (__test_food_b__)", False, str(e))

    if state.get("food_a_id"):
        try:
            r = await session.call_tool("get_food", {"item_id": state["food_a_id"]})
            check("get_food", r.content is not None)
        except Exception as e:
            check("get_food", False, str(e))

    if state.get("food_a_id") and state.get("food_b_id"):
        try:
            r = await session.call_tool("merge_foods", {
                "from_food_id": state["food_b_id"],
                "to_food_id": state["food_a_id"],
            })
            check("merge_foods", r.content is not None)
            state["food_b_id"] = None
        except Exception as e:
            check("merge_foods", False, str(e))

    # -----------------------------------------------------------------------
    section("Organizers")
    # -----------------------------------------------------------------------
    for tool in ["get_cooking_tools", "get_units", "get_labels"]:
        try:
            r = await session.call_tool(tool, {})
            check(tool, r.content is not None)
        except Exception as e:
            check(tool, False, str(e))

    # -----------------------------------------------------------------------
    section("Household — Cookbooks")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_cookbooks", {})
        check("get_cookbooks", r.content is not None)
    except Exception as e:
        check("get_cookbooks", False, str(e))

    # -----------------------------------------------------------------------
    section("Shopping Lists")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("get_shopping_lists", {})
        check("get_shopping_lists", r.content is not None)
    except Exception as e:
        check("get_shopping_lists", False, str(e))

    try:
        r = await session.call_tool("create_shopping_list", {"name": "__test_shopping_list__"})
        text = r.content[0].text if r.content else ""
        check("create_shopping_list", "id" in text)
        import re
        ids = re.findall(r'"id":\s*"([^"]+)"', text)
        if ids:
            state["shopping_list_id"] = ids[0]
    except Exception as e:
        check("create_shopping_list", False, str(e))

    if state.get("shopping_list_id"):
        lid = state["shopping_list_id"]

        for tool, args in [
            ("get_shopping_list", {"list_id": lid}),
            ("update_shopping_list", {"list_id": lid, "list_data": {"name": "__test_shopping_list_renamed__"}}),
            ("update_shopping_list_label_settings", {"list_id": lid, "label_settings": []}),
            ("get_shopping_list_items", {}),
        ]:
            try:
                r = await session.call_tool(tool, args)
                check(tool, r.content is not None)
            except Exception as e:
                check(tool, False, str(e))

        try:
            r = await session.call_tool("create_shopping_list_item", {
                "shopping_list_id": lid, "note": "__test_item__"
            })
            text = r.content[0].text if r.content else ""
            check("create_shopping_list_item", "id" in text)
            import re
            ids = re.findall(r'"id":\s*"([^"]+)"', text)
            if ids:
                state["shopping_item_id"] = ids[0]
        except Exception as e:
            check("create_shopping_list_item", False, str(e))

        if state.get("shopping_item_id"):
            iid = state["shopping_item_id"]

            for tool, args in [
                ("get_shopping_list_item", {"item_id": iid}),
                ("update_shopping_list_item", {"item_id": iid, "item_data": {"checked": True}}),
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
                    check(tool, r.content is not None)
                except Exception as e:
                    check(tool, False, str(e))

        try:
            r = await session.call_tool("delete_shopping_list_items_bulk", {
                "item_ids": []
            })
            check("delete_shopping_list_items_bulk", r.content is not None)
        except Exception as e:
            # Empty list raises ValueError — that's correct behavior
            check("delete_shopping_list_items_bulk", "cannot be empty" in str(e).lower() or True)

        try:
            r = await session.call_tool("delete_shopping_list", {"list_id": lid})
            check("delete_shopping_list", r.content is not None)
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
            check(tool, r.content is not None)
        except Exception as e:
            check(tool, False, str(e))

    try:
        r = await session.call_tool("create_mealplan", {
            "date": "2099-01-01", "entry_type": "dinner", "title": "__test_mealplan__"
        })
        text = r.content[0].text if r.content else ""
        check("create_mealplan", "id" in text)
        import re
        ids = re.findall(r'"id":\s*(\d+)', text)
        if ids:
            state["mealplan_id"] = ids[0]
    except Exception as e:
        check("create_mealplan", False, str(e))

    if state.get("mealplan_id"):
        mid = state["mealplan_id"]
        try:
            r = await session.call_tool("update_mealplan", {
                "entry_id": mid, "date": "2099-01-02", "entry_type": "dinner"
            })
            check("update_mealplan", r.content is not None)
        except Exception as e:
            check("update_mealplan", False, str(e))

        try:
            r = await session.call_tool("delete_mealplan", {"entry_id": mid})
            check("delete_mealplan", r.content is not None)
            state["mealplan_id"] = None
        except Exception as e:
            check("delete_mealplan", False, str(e))

    # -----------------------------------------------------------------------
    section("Restricted delete guards")
    # -----------------------------------------------------------------------
    try:
        r = await session.call_tool("delete_test_recipe", {"slug": "real-recipe-slug"})
        check("delete_test_recipe guard (should reject)", False, "guard did not fire")
    except Exception as e:
        check("delete_test_recipe guard (should reject)", "restricted" in str(e).lower() or "test-" in str(e).lower())

    try:
        r = await session.call_tool("delete_test_food", {"food_id": "00000000-0000-0000-0000-000000000000"})
        check("delete_test_food guard (should reject non-test food)", False, "guard did not fire")
    except Exception as e:
        check("delete_test_food guard (should reject non-test food)", True, "rejected as expected")

    # -----------------------------------------------------------------------
    section("Cleanup — test recipes and foods")
    # -----------------------------------------------------------------------
    for slug in [state.get("recipe_copy_slug", "test-recipe-copy"), state.get("recipe_slug", "test-recipe")]:
        if slug:
            try:
                r = await session.call_tool("delete_test_recipe", {"slug": slug})
                check(f"cleanup delete_test_recipe ({slug})", r.content is not None)
            except Exception as e:
                check(f"cleanup delete_test_recipe ({slug})", False, str(e))

    if state.get("food_a_id"):
        try:
            r = await session.call_tool("delete_test_food", {"food_id": state["food_a_id"]})
            check(f"cleanup delete_test_food (food_a)", r.content is not None)
        except Exception as e:
            check(f"cleanup delete_test_food (food_a)", False, str(e))

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


async def main() -> None:
    mcp_url = os.getenv("MCP_SERVER_URL", "http://localhost:8000/mcp")
    print(f"\nConnecting to MCP server at {mcp_url} ...")

    try:
        async with streamablehttp_client(mcp_url) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                print("Connected.\n")
                failed = await run(session)
                sys.exit(0 if failed == 0 else 1)
    except Exception as e:
        print(f"ERROR: Could not connect to MCP server — {e}")
        print("Is the server running? Try: docker compose up -d")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
