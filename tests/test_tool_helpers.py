"""
Script 6: tool helper unit tests (Mealie v3.30 compatibility).

No live infrastructure — exercises logic against stand-in objects:
- whole-week meal plan alignment for every household firstDayOfWeek setting
  (the integration tests can only see the live household's own setting)
- the recipe read tools when the household lastMade lookup fails
- shopping list tools trimming recipeReferences
- reordering a shopping list's sections by label name
- create_mealplan / create_mealplan_bulk: trimmed entries, checks before creating,
  partial-failure report

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
from tools.mealplan_tools import register_mealplan_tools
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


class FakeLabels:
    """A list with four labels in alphabetical order; records the label settings PUT."""

    NAMES = ["Baking", "Fruits", "Meats", "Vegetables & Greens"]

    def __init__(self):
        self.puts = []
        self.settings = [
            {"id": f"S{i}", "shoppingListId": "L1", "labelId": f"LBL{i}", "position": i,
             "label": {"id": f"LBL{i}", "name": name}}
            for i, name in enumerate(self.NAMES)
        ]

    def get_shopping_list(self, list_id):
        return {"id": "L1", "name": "Groceries", "labelSettings": self.settings}

    def update_shopping_list_label_settings(self, list_id, payload):
        self.puts.append(payload)
        by_id = {st["id"]: st for st in self.settings}
        self.settings = [{**by_id[p["id"]], "position": p["position"]} for p in payload]
        return self.get_shopping_list(list_id)


class FakeMealplanCreate:
    """Creates entries like Mealie (with the embedded recipe); fails on title "boom"."""

    def __init__(self):
        self.created = []

    def create_mealplan(self, date, recipe_id=None, title=None, entry_type="breakfast", whole_week=False):
        if title == "boom":
            raise ConnectionError("Mealie unavailable")
        entry = {"id": len(self.created) + 1, "date": date, "endDate": None, "entryType": entry_type,
                 "title": title or "", "text": "", "recipeId": recipe_id, "groupId": "g", "userId": "u",
                 "householdId": "h", "recipe": None}
        if whole_week:
            entry["endDate"] = "2099-03-07"
        if recipe_id:
            entry["recipe"] = {"id": recipe_id, "name": "Chili Sauce", "slug": "chili-sauce",
                               "description": "long text", "tags": []}
        self.created.append(entry)
        return entry


RECIPE_UUID = "8896a171-9789-4f71-8a39-849e1ad67714"


def call_error(srv: FastMCP, tool: str, args: dict) -> str:
    try:
        call(srv, tool, args)
    except Exception as e:
        return str(e)
    return ""


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
    section("Shopping list section order by label name")
    # ------------------------------------------------------------------
    fake = FakeLabels()
    srv = FastMCP("probe")
    register_shopping_list_tools(srv, fake)
    out = call(srv, "update_shopping_list_label_settings",
               {"list_id": "L1", "labels": ["vegetables & greens", "FRUITS", "Fruits"]})
    check("named labels first (any case, duplicates ignored), the rest keep their order",
          out.get("labelOrder") == ["Vegetables & Greens", "Fruits", "Baking", "Meats"], str(out))
    put = fake.puts[-1] if fake.puts else []
    check("sends every setting with id, shoppingListId, labelId and position",
          [(p["id"], p["shoppingListId"], p["labelId"], p["position"]) for p in put]
          == [("S3", "L1", "LBL3", 0), ("S1", "L1", "LBL1", 1), ("S0", "L1", "LBL0", 2), ("S2", "L1", "LBL2", 3)],
          str(put))
    out = call(srv, "update_shopping_list_label_settings", {"list_id": "L1", "labels": ["LBL2"]})
    check("a label id is accepted too", out.get("labelOrder", [None])[0] == "Meats", str(out))

    puts = len(fake.puts)
    err = call_error(srv, "update_shopping_list_label_settings",
                     {"list_id": "L1", "labels": ["Meats", "Produce"]})
    check("unknown name: error names it and lists the real labels",
          '"Produce"' in err and all(n in err for n in FakeLabels.NAMES), err)
    check("unknown name: nothing sent to Mealie", len(fake.puts) == puts)
    err = call_error(srv, "update_shopping_list_label_settings", {"list_id": "L1", "labels": []})
    check("empty list rejected without sending", bool(err) and len(fake.puts) == puts, err)

    # ------------------------------------------------------------------
    section("Meal plan create: trimmed entries, checks first, partial failures")
    # ------------------------------------------------------------------
    fake = FakeMealplanCreate()
    srv = FastMCP("probe")
    register_mealplan_tools(srv, fake)
    out = call(srv, "create_mealplan", {"date": "2099-03-04", "recipe_id": RECIPE_UUID, "entry_type": "dinner"})
    check("create_mealplan returns the trimmed entry with its id",
          out == {"id": 1, "date": "2099-03-04", "entryType": "dinner", "recipeId": RECIPE_UUID,
                  "recipeName": "Chili Sauce", "recipeSlug": "chili-sauce"}, str(out))
    out = call(srv, "create_mealplan_bulk", {"entries": [
        {"date": "2099-03-05", "title": "Leftovers", "entry_type": "lunch"},
        {"date": "2099-03-04", "title": "Soup week", "entry_type": "dinner", "whole_week": True},
    ]})
    check("create_mealplan_bulk returns every created entry in order with ids",
          out == {"created": [
              {"id": 2, "date": "2099-03-05", "entryType": "lunch", "title": "Leftovers"},
              {"id": 3, "date": "2099-03-04", "endDate": "2099-03-07", "entryType": "dinner", "title": "Soup week"},
          ]}, str(out))

    before = len(fake.created)
    for name, entry, expect in [
        ("bad entry_type", {"date": "2099-03-06", "title": "x", "entry_type": "brunch"}, "brunch"),
        ("bad date", {"date": "03/06/2099", "title": "x"}, "YYYY-MM-DD"),
        ("no recipe or title", {"date": "2099-03-06"}, "recipe_id or a title"),
        ("recipe_id not a UUID", {"date": "2099-03-06", "recipe_id": "chili-sauce"}, "not a recipe UUID"),
        ("unknown key", {"date": "2099-03-06", "title": "x", "entryType": "dinner"}, "entryType"),
    ]:
        err = call_error(srv, "create_mealplan_bulk", {"entries": [
            {"date": "2099-03-06", "title": "fine"}, entry]})
        check(f"bulk {name}: rejected, names entry 2, nothing created",
              expect in err and "entry 2" in err and "nothing was created" in err
              and len(fake.created) == before, err[-160:])
    err = call_error(srv, "create_mealplan", {"date": "2099-03-06", "title": "x", "entry_type": "brunch"})
    check("create_mealplan rejects a bad entry_type before creating",
          "brunch" in err and len(fake.created) == before, err[-120:])

    err = call_error(srv, "create_mealplan_bulk", {"entries": [
        {"date": "2099-03-08", "title": "a"}, {"date": "2099-03-09", "title": "b"},
        {"date": "2099-03-10", "title": "boom"}, {"date": "2099-03-11", "title": "d"},
    ]})
    check("bulk partial failure: reports created ids, the failed entry and what was not attempted",
          f"Created 2 of 4 entries (ids {before + 1}, {before + 2})" in err
          and "entry 3 (2099-03-10) failed" in err and "entry 4 was not attempted" in err, err[-260:])

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
