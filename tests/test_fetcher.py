"""
Script 1: MealieFetcher integration tests.

Tests every mixin method directly against the Mealie API.
No MCP server required — runs anywhere Python runs.

Usage:
    cd mealie-mcp-server
    cp tests/.env.testing.template tests/.env.testing
    # edit tests/.env.testing with your values
    python tests/test_fetcher.py
"""

import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.testing"))

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mealie import MealieFetcher
from mealie.client import MealieApiError

log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logging.basicConfig(
    level=log_level,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler()],
)

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"

results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    status = PASS if condition else FAIL
    print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, condition, detail))


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def run(mealie: MealieFetcher) -> None:
    # IDs collected during the run for use in later tests and cleanup
    state: dict = {}

    # -----------------------------------------------------------------------
    section("Pre-test cleanup — remove stale test artifacts")
    # -----------------------------------------------------------------------
    for slug in ["test-recipe-copy", "test-recipe"]:
        try:
            mealie.delete_recipe(slug)
            print(f"  [cleanup] deleted stale recipe: {slug}")
        except Exception:
            pass

    try:
        foods = mealie.get_foods(search="__test_food", per_page=50)
        for f in foods.get("items", []):
            if f.get("name", "").startswith("__test_"):
                try:
                    mealie.delete_food(f["id"])
                    print(f"  [cleanup] deleted stale food: {f['name']}")
                except Exception:
                    pass
    except Exception:
        pass

    # -----------------------------------------------------------------------
    section("Recipes — read")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_recipes(per_page=5)
        check("get_recipes", "items" in r)
    except Exception as e:
        check("get_recipes", False, str(e))

    # -----------------------------------------------------------------------
    section("Recipes — create and inspect")
    # -----------------------------------------------------------------------
    try:
        slug = mealie.create_recipe("__test_recipe__")
        state["recipe_slug"] = slug if isinstance(slug, str) else slug.get("slug")
        check("create_recipe POST", bool(state.get("recipe_slug")), state.get("recipe_slug", ""))
    except Exception as e:
        check("create_recipe POST", False, str(e))

    if state.get("recipe_slug"):
        slug = state["recipe_slug"]
        try:
            patch_data = {
                "description": "Automated test recipe — safe to delete",
                "recipeCategory": [],
                "tags": [],
                "recipeIngredient": [],
                "recipeInstructions": [
                    {"title": "", "text": "Test step 1", "summary": "", "ingredientReferences": []},
                    {"title": "", "text": "Test step 2", "summary": "", "ingredientReferences": []},
                ],
                "recipeYield": "1 serving",
            }
            r = mealie.patch_recipe(slug, patch_data)
            check("create_recipe PATCH (full data)", isinstance(r, dict))
        except Exception as e:
            check("create_recipe PATCH (full data)", False, str(e))

        try:
            # Mealie requires food.id on PATCH — a name-only food object must 500
            bad_patch = {
                "recipeIngredient": [
                    {"quantity": 1.0, "disableAmount": False, "food": {"name": "__test_nameless_food__"}}
                ]
            }
            mealie.patch_recipe(slug, bad_patch)
            check("patch_recipe rejects name-only food (no id)", False, "expected 500 but got success")
        except MealieApiError as e:
            check("patch_recipe rejects name-only food (no id)", e.status_code == 500, str(e)[:80])
        except Exception as e:
            check("patch_recipe rejects name-only food (no id)", False, str(e))

        try:
            r = mealie.get_recipe(slug)
            state["recipe_id"] = r.get("id")
            check("get_recipe_detailed", r.get("slug") == slug)
        except Exception as e:
            check("get_recipe_detailed", False, str(e))

        try:
            r = mealie.duplicate_recipe(slug, name="__test_recipe_copy__")
            state["recipe_copy_slug"] = r.get("slug") if isinstance(r, dict) else None
            check("duplicate_recipe", bool(state.get("recipe_copy_slug")), state.get("recipe_copy_slug", ""))
        except Exception as e:
            check("duplicate_recipe", False, str(e))

        try:
            r = mealie.update_recipe_last_made(slug)
            check("mark_recipe_last_made", isinstance(r, dict))
        except Exception as e:
            check("mark_recipe_last_made", False, str(e))

        try:
            r = mealie.get_recipe_comments(slug)
            check("get_recipe_comments", isinstance(r, list))
        except Exception as e:
            check("get_recipe_comments", False, str(e))

        try:
            r = mealie.create_recipe_comment(slug, "Automated test comment")
            check("create_recipe_comment", isinstance(r, dict))
        except Exception as e:
            check("create_recipe_comment", False, str(e))

        try:
            r = mealie.get_recipe_timeline()
            check("get_recipe_timeline", "items" in r)
        except Exception as e:
            check("get_recipe_timeline", False, str(e))

        try:
            r = mealie.get_recipe_share_tokens(slug)
            check("get_recipe_share_tokens", isinstance(r, list))
        except Exception as e:
            check("get_recipe_share_tokens", False, str(e))

        try:
            r = mealie.create_recipe_share_token(slug)
            check("create_recipe_share_token", isinstance(r, dict))
        except Exception as e:
            check("create_recipe_share_token", False, str(e))

        try:
            r = mealie.get_recipe_exports(slug)
            check("get_recipe_exports", isinstance(r, (dict, list)))
        except Exception as e:
            check("get_recipe_exports", False, str(e))

    # -----------------------------------------------------------------------
    section("Categories")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_categories(per_page=50)
        check("get_categories", "items" in r)
        if r.get("items"):
            cat = r["items"][0]
            state["category_id"] = cat["id"]
            state["category_slug"] = cat["slug"]
    except Exception as e:
        check("get_categories", False, str(e))

    if state.get("category_id"):
        try:
            r = mealie.get_category(state["category_id"])
            check("get_category", "id" in r)
        except Exception as e:
            check("get_category", False, str(e))

    if state.get("category_slug"):
        try:
            r = mealie.get_category_by_slug(state["category_slug"])
            check("get_category_by_slug", "slug" in r)
        except Exception as e:
            check("get_category_by_slug", False, str(e))

    try:
        r = mealie.get_empty_categories()
        check("get_empty_categories", isinstance(r, (dict, list)))
    except Exception as e:
        check("get_empty_categories", False, str(e))

    # -----------------------------------------------------------------------
    section("Tags")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_tags(per_page=50)
        check("get_tags", "items" in r)
        if r.get("items"):
            tag = r["items"][0]
            state["tag_id"] = tag["id"]
            state["tag_slug"] = tag["slug"]
    except Exception as e:
        check("get_tags", False, str(e))

    if state.get("tag_id"):
        try:
            r = mealie.get_tag(state["tag_id"])
            check("get_tag", "id" in r)
        except Exception as e:
            check("get_tag", False, str(e))

    if state.get("tag_slug"):
        try:
            r = mealie.get_tag_by_slug(state["tag_slug"])
            check("get_tag_by_slug", "slug" in r)
        except Exception as e:
            check("get_tag_by_slug", False, str(e))

    try:
        r = mealie.get_empty_tags()
        check("get_empty_tags", isinstance(r, (dict, list)))
    except Exception as e:
        check("get_empty_tags", False, str(e))

    # -----------------------------------------------------------------------
    section("Foods")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_foods(per_page=50)
        check("get_foods", "items" in r)
        if r.get("items"):
            state["food_id"] = r["items"][0]["id"]
    except Exception as e:
        check("get_foods", False, str(e))

    if state.get("food_id"):
        try:
            r = mealie.get_food(state["food_id"])
            check("get_food", "id" in r)
        except Exception as e:
            check("get_food", False, str(e))

    try:
        r = mealie.create_food("__test_food_a__")
        state["food_a_id"] = r.get("id")
        check("create_food (__test_food_a__)", bool(state.get("food_a_id")))
    except Exception as e:
        check("create_food (__test_food_a__)", False, str(e))

    try:
        r = mealie.create_food("__test_food_b__")
        state["food_b_id"] = r.get("id")
        check("create_food (__test_food_b__)", bool(state.get("food_b_id")))
    except Exception as e:
        check("create_food (__test_food_b__)", False, str(e))

    if state.get("food_a_id") and state.get("food_b_id"):
        try:
            r = mealie.merge_foods(state["food_b_id"], state["food_a_id"])
            check("merge_foods (b → a)", isinstance(r, dict))
            state["food_b_id"] = None  # deleted by merge
        except Exception as e:
            check("merge_foods (b → a)", False, str(e))

    # -----------------------------------------------------------------------
    section("Organizers")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_organizer_tools(per_page=50)
        check("get_cooking_tools", "items" in r)
    except Exception as e:
        check("get_cooking_tools", False, str(e))

    try:
        r = mealie.get_organizer_units(per_page=50)
        check("get_units", "items" in r)
    except Exception as e:
        check("get_units", False, str(e))

    try:
        r = mealie.get_organizer_labels(per_page=50)
        check("get_labels", "items" in r)
    except Exception as e:
        check("get_labels", False, str(e))

    # -----------------------------------------------------------------------
    section("Household — Cookbooks")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_cookbooks()
        check("get_cookbooks", "items" in r)
    except Exception as e:
        check("get_cookbooks", False, str(e))

    # -----------------------------------------------------------------------
    section("Shopping Lists")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_shopping_lists()
        check("get_shopping_lists", "items" in r)
    except Exception as e:
        check("get_shopping_lists", False, str(e))

    try:
        r = mealie.create_shopping_list(name="__test_shopping_list__")
        state["shopping_list_id"] = r.get("id")
        check("create_shopping_list", bool(state.get("shopping_list_id")))
    except Exception as e:
        check("create_shopping_list", False, str(e))

    if state.get("shopping_list_id"):
        lid = state["shopping_list_id"]

        try:
            r = mealie.get_shopping_list(lid)
            check("get_shopping_list", r.get("id") == lid)
        except Exception as e:
            check("get_shopping_list", False, str(e))

        try:
            r = mealie.update_shopping_list(lid, {"name": "__test_shopping_list_renamed__"})
            check("update_shopping_list", isinstance(r, dict))
        except Exception as e:
            check("update_shopping_list", False, str(e))

        try:
            r = mealie.update_shopping_list_label_settings(lid, [])
            check("update_shopping_list_label_settings", isinstance(r, (dict, list)))
        except Exception as e:
            check("update_shopping_list_label_settings", False, str(e))

        try:
            r = mealie.get_shopping_list_items()
            check("get_shopping_list_items", "items" in r)
        except Exception as e:
            check("get_shopping_list_items", False, str(e))

        try:
            r = mealie.create_shopping_list_item(shopping_list_id=lid, note="__test_item__")
            state["shopping_item_id"] = r.get("id")
            check("create_shopping_list_item", bool(state.get("shopping_item_id")))
        except Exception as e:
            check("create_shopping_list_item", False, str(e))

        if state.get("shopping_item_id"):
            iid = state["shopping_item_id"]

            try:
                r = mealie.get_shopping_list_item(iid)
                check("get_shopping_list_item", r.get("id") == iid)
            except Exception as e:
                check("get_shopping_list_item", False, str(e))

            try:
                r = mealie.update_shopping_list_item(iid, {"checked": True})
                check("update_shopping_list_item", isinstance(r, dict))
            except Exception as e:
                check("update_shopping_list_item", False, str(e))

            try:
                r = mealie.create_shopping_list_items_bulk(
                    items=[{"shoppingListId": lid, "note": "__test_bulk_item__", "checked": False}]
                )
                check("create_shopping_list_items_bulk", isinstance(r, (dict, list)))
            except Exception as e:
                check("create_shopping_list_items_bulk", False, str(e))

            try:
                current = mealie.get_shopping_list_item(iid)
                r = mealie.update_shopping_list_items_bulk(
                    items=[{**current, "checked": False}]
                )
                check("update_shopping_list_items_bulk", isinstance(r, (dict, list)))
            except Exception as e:
                check("update_shopping_list_items_bulk", False, str(e))

            try:
                r = mealie.delete_shopping_list_item(iid)
                check("delete_shopping_list_item", isinstance(r, dict))
                state["shopping_item_id"] = None
            except Exception as e:
                check("delete_shopping_list_item", False, str(e))

        # Recipe integration tests require a recipe UUID (not slug)
        recipe_id = state.get("recipe_id")
        if recipe_id:
            try:
                r = mealie.add_recipe_to_shopping_list(lid, recipe_id)
                check("add_recipe_to_shopping_list", isinstance(r, (dict, list)))
            except Exception as e:
                check("add_recipe_to_shopping_list", False, str(e))

            try:
                r = mealie.remove_recipe_from_shopping_list(lid, recipe_id)
                check("remove_recipe_from_shopping_list", isinstance(r, (dict, list)))
            except Exception as e:
                check("remove_recipe_from_shopping_list", False, str(e))

            try:
                r = mealie.add_recipes_to_shopping_list_bulk(
                    lid, [{"recipeId": recipe_id, "recipeIncrementQuantity": 1}]
                )
                check("add_recipes_to_shopping_list_bulk", isinstance(r, (dict, list)))
            except Exception as e:
                check("add_recipes_to_shopping_list_bulk", False, str(e))

        # Collect remaining item IDs for bulk delete
        try:
            all_items = mealie.get_shopping_list_items()
            test_item_ids = [
                i["id"] for i in all_items.get("items", [])
                if i.get("shoppingListId") == lid
            ]
            if test_item_ids:
                r = mealie.delete_shopping_list_items_bulk(item_ids=test_item_ids)
                check("delete_shopping_list_items_bulk", isinstance(r, (dict, list)))
            else:
                check("delete_shopping_list_items_bulk", True, "no items to delete")
        except Exception as e:
            check("delete_shopping_list_items_bulk", False, str(e))

        try:
            r = mealie.delete_shopping_list(lid)
            check("delete_shopping_list", isinstance(r, dict))
            state["shopping_list_id"] = None
        except Exception as e:
            check("delete_shopping_list", False, str(e))

    # -----------------------------------------------------------------------
    section("Meal Plans")
    # -----------------------------------------------------------------------
    try:
        r = mealie.get_mealplans()
        check("get_all_mealplans", "items" in r)
    except Exception as e:
        check("get_all_mealplans", False, str(e))

    try:
        r = mealie.get_todays_mealplan()
        check("get_todays_mealplan", isinstance(r, (dict, list)))
    except Exception as e:
        check("get_todays_mealplan", False, str(e))

    recipe_id = state.get("recipe_id")
    if recipe_id:
        try:
            r = mealie.create_mealplan(date="2099-01-01", entry_type="dinner", recipe_id=recipe_id)
            state["mealplan_id"] = r.get("id")
            check("create_mealplan", bool(state.get("mealplan_id")))
        except Exception as e:
            check("create_mealplan", False, str(e))

    if state.get("mealplan_id"):
        mid = state["mealplan_id"]
        try:
            r = mealie.update_mealplan(mid, date="2099-01-02", entry_type="dinner")
            check("update_mealplan", isinstance(r, dict))
        except Exception as e:
            check("update_mealplan", False, str(e))

        try:
            r = mealie.delete_mealplan(mid)
            check("delete_mealplan", isinstance(r, dict))
            state["mealplan_id"] = None
        except Exception as e:
            check("delete_mealplan", False, str(e))

    # -----------------------------------------------------------------------
    section("Cleanup — test recipes and foods")
    # -----------------------------------------------------------------------
    for slug in [state.get("recipe_copy_slug"), state.get("recipe_slug")]:
        if slug:
            try:
                r = mealie.delete_recipe(slug)
                check(f"cleanup delete_recipe ({slug})", isinstance(r, dict))
            except Exception as e:
                check(f"cleanup delete_recipe ({slug})", False, str(e))

    for fid in [state.get("food_b_id"), state.get("food_a_id")]:
        if fid:
            try:
                r = mealie.delete_food(fid)
                check(f"cleanup delete_food ({fid})", isinstance(r, dict))
            except Exception as e:
                check(f"cleanup delete_food ({fid})", False, str(e))

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
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    base_url = os.getenv("MEALIE_BASE_URL")
    api_key = os.getenv("MEALIE_API_KEY")

    if not base_url or not api_key:
        print("ERROR: MEALIE_BASE_URL and MEALIE_API_KEY must be set in .env.testing")
        sys.exit(1)

    print(f"\nConnecting to Mealie at {base_url} ...")
    try:
        mealie = MealieFetcher(base_url=base_url, api_key=api_key)
    except Exception as e:
        print(f"ERROR: Could not connect — {e}")
        sys.exit(1)

    print("Connected.\n")
    run(mealie)
