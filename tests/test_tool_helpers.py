"""
Script 6: tool helper unit tests (Mealie v3.30 compatibility).

No live infrastructure — exercises logic against stand-in objects:
- whole-week meal plan alignment for every household firstDayOfWeek setting
  (the integration tests can only see the live household's own setting)
- the recipe read tools when the household lastMade lookup fails
- shopping list tools trimming recipeReferences

Usage:
    cd mealie-mcp-server
    python tests/test_tool_helpers.py
"""

import asyncio
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mcp.server.fastmcp import FastMCP

from mealie.mealplan import MealplanMixin
from tools.recipe_tools import register_recipe_tools
from tools.shopping_list_tools import register_shopping_list_tools

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, bool(condition), detail))


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


class FakeMealplan(MealplanMixin):
    """MealplanMixin with the household preference stubbed out."""

    def __init__(self, first_day):
        self.first_day = first_day

    def get_household_preferences(self):
        return {"firstDayOfWeek": self.first_day}


class FakeRecipes:
    """Stands in for MealieFetcher in the recipe tools."""

    def __init__(self, last_made_error: bool):
        self.last_made_error = last_made_error

    def get_recipe(self, slug):
        return {
            "id": "1", "userId": "u", "householdId": "h", "groupId": "g",
            "name": "Chili Sauce", "slug": slug,
            "dateAdded": "2026-01-01", "dateUpdated": "2026-01-01",
            "createdAt": "2026-01-01", "updatedAt": "2026-01-01",
            "prepTime": None, "prepTimeSeconds": 3600,
            "performTime": None, "performTimeSeconds": 7200,
            "totalTime": None, "totalTimeSeconds": 10800,
        }

    def get_household_recipe(self, slug):
        if self.last_made_error:
            raise ConnectionError("household lookup failed")
        return {"recipeId": "1", "lastMade": "2026-11-01T18:00:00Z"}


FULL_LIST = {
    "id": "L1", "name": "Groceries", "listItems": [], "labelSettings": [],
    "recipeReferences": [{
        "id": "ref1", "shoppingListId": "L1", "recipeId": "R1", "recipeQuantity": 2.0,
        "recipe": {"id": "R1", "name": "Chili Sauce", "slug": "chili-sauce",
                   "description": "long text", "tags": [{"name": "t", "recipeCount": 0}]},
    }],
}


class FakeShopping:
    """Stands in for MealieFetcher in the shopping list tools; records what it was sent."""

    def __init__(self):
        self.sent = []

    def get_shopping_lists(self, page=None, per_page=None):
        return {"page": 1, "total": 1, "items": [FULL_LIST]}

    def get_shopping_list(self, list_id):
        return FULL_LIST

    def create_shopping_list(self, name):
        return FULL_LIST

    def update_shopping_list(self, list_id, data):
        self.sent.append(data)
        return FULL_LIST

    def delete_shopping_list(self, list_id):
        return FULL_LIST

    def add_recipe_to_shopping_list(self, list_id, recipe_id, qty):
        return FULL_LIST

    def remove_recipe_from_shopping_list(self, list_id, recipe_id):
        return FULL_LIST

    def add_recipes_to_shopping_list_bulk(self, list_id, recipes):
        return FULL_LIST


def call(srv: FastMCP, tool: str, args: dict) -> dict:
    result = asyncio.run(srv.call_tool(tool, args))
    content = result[0] if isinstance(result, tuple) else result
    return json.loads(content[0].text)


def run() -> None:
    # ------------------------------------------------------------------
    section("Whole-week entries align to firstDayOfWeek (0=Sunday ... 6=Saturday)")
    # ------------------------------------------------------------------
    for first in range(7):
        mixin = FakeMealplan(first)
        bad = []
        for offset in range(14):  # two full weeks, so every weekday is a requested day
            day = date(2099, 1, 1) + timedelta(days=offset)
            start, end = (date.fromisoformat(d) for d in mixin.week_range(day.isoformat()))
            if not ((start.weekday() + 1) % 7 == first and start <= day <= end
                    and end == start + timedelta(days=6)):
                bad.append(f"{day}->{start}..{end}")
        check(f"firstDayOfWeek={first}: every day maps into a 7-day week starting that weekday",
              not bad, ", ".join(bad[:3]))

    # Wed 2099-01-07: Sunday week starts 01-04, Monday week starts 01-05
    check("Sunday week of Wed 2099-01-07 is 01-04..01-10",
          FakeMealplan(0).week_range("2099-01-07") == ("2099-01-04", "2099-01-10"))
    check("Monday week of Wed 2099-01-07 is 01-05..01-11",
          FakeMealplan(1).week_range("2099-01-07") == ("2099-01-05", "2099-01-11"))
    check("no preference set defaults to a Sunday week",
          FakeMealplan(None).week_range("2099-01-07") == ("2099-01-04", "2099-01-10"))

    # ------------------------------------------------------------------
    section("Recipe read tools: readable times + lastMade")
    # ------------------------------------------------------------------
    srv = FastMCP("probe")
    register_recipe_tools(srv, FakeRecipes(last_made_error=False))
    c = call(srv, "get_recipe_concise", {"slug": "chili"})
    check("concise: readable totalTime from seconds", c.get("totalTime") == "3 hours", str(c))
    check("concise: lastMade from household data", c.get("lastMade") == "2026-11-01T18:00:00Z", str(c))
    d = call(srv, "get_recipe_detailed", {"slug": "chili"})
    check("detailed: readable times and seconds",
          (d.get("prepTime"), d.get("performTime"), d.get("totalTime"), d.get("totalTimeSeconds"))
          == ("1 hour", "2 hours", "3 hours", 10800), str(d))

    srv = FastMCP("probe")
    register_recipe_tools(srv, FakeRecipes(last_made_error=True))
    try:
        c = call(srv, "get_recipe_concise", {"slug": "chili"})
        check("concise: failed lastMade lookup still returns the recipe",
              c.get("name") == "Chili Sauce" and c.get("totalTime") == "3 hours" and "lastMade" not in c,
              str(c))
    except Exception as e:
        check("concise: failed lastMade lookup still returns the recipe", False, repr(e))
    try:
        d = call(srv, "get_recipe_detailed", {"slug": "chili"})
        check("detailed: failed lastMade lookup still returns the recipe",
              d.get("name") == "Chili Sauce" and d.get("totalTime") == "3 hours", str(d))
    except Exception as e:
        check("detailed: failed lastMade lookup still returns the recipe", False, repr(e))

    # ------------------------------------------------------------------
    section("Shopping list tools trim recipeReferences")
    # ------------------------------------------------------------------
    trimmed = [{"recipeId": "R1", "name": "Chili Sauce", "slug": "chili-sauce", "recipeQuantity": 2.0}]
    fake = FakeShopping()
    srv = FastMCP("probe")
    register_shopping_list_tools(srv, fake)
    for tool, args in [
        ("get_shopping_list", {"list_id": "L1"}),
        ("create_shopping_list", {"name": "Groceries"}),
        ("update_shopping_list", {"list_id": "L1", "name": "Groceries"}),
        ("delete_shopping_list", {"list_id": "L1"}),
        ("add_recipe_to_shopping_list", {"list_id": "L1", "recipe_id": "R1"}),
        ("remove_recipe_from_shopping_list", {"list_id": "L1", "recipe_id": "R1"}),
        ("add_recipes_to_shopping_list_bulk", {"list_id": "L1", "recipes": [{"recipeId": "R1"}]}),
    ]:
        out = call(srv, tool, args)
        check(f"{tool}: recipeReferences trimmed", out.get("recipeReferences") == trimmed,
              str(out.get("recipeReferences"))[:120])
    out = call(srv, "get_shopping_lists", {})
    check("get_shopping_lists: every list's recipeReferences trimmed",
          [i.get("recipeReferences") for i in out.get("items", [])] == [trimmed], str(out)[:120])
    check("rename sends only the new name (full list is merged by the fetcher, untrimmed)",
          fake.sent == [{"name": "Groceries"}], str(fake.sent))
    check("source data left untouched", "recipe" in FULL_LIST["recipeReferences"][0])

    # ------------------------------------------------------------------
    section("Summary")
    # ------------------------------------------------------------------
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    total = len(results)
    print(f"\n  {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} failed)\n\nFailed:")
        for name, ok, detail in results:
            if not ok:
                print(f"  - {name}" + (f": {detail}" if detail else ""))
    else:
        print(" — all tests passed")
    print()
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    run()
