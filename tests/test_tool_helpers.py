"""
Script 6: tool helper unit tests (Mealie v3.30 compatibility).

No live infrastructure — exercises logic against stand-in objects:
- whole-week meal plan alignment for every household firstDayOfWeek setting
  (the integration tests can only see the live household's own setting)
- the recipe read tools when the household lastMade lookup fails
- recipe read tools trimming Mealie's nested copies (get_recipes, concise, detailed)
- shopping list tools trimming lists and items (labelOrder, recipeReferences, items)
- reordering a shopping list's sections by label name
- create_mealplan / create_mealplan_bulk / update_mealplan: trimmed entries, checks before creating,
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


def organizer(name, slug, **extra):
    return {"id": f"id-{slug}", "groupId": "g", "name": name, "slug": slug, "recipeCount": 0, **extra}


LABEL = {"name": "Fruits", "color": "#7CB342", "groupId": "g", "id": "lab-1"}
TOMATO = {"id": "food-1", "name": "tomato", "pluralName": "tomatoes", "description": "", "extras": {},
          "labelId": "lab-1", "aliases": [], "substitutions": [], "householdsWithIngredientFood": [],
          "label": LABEL, "recipeCount": 0, "createdAt": "2026-04-13", "updatedAt": "2026-04-13"}
CUP = {"id": "unit-1", "name": "cup", "pluralName": "cups", "description": "", "extras": {}, "fraction": True,
       "abbreviation": "c", "pluralAbbreviation": "", "useAbbreviation": False, "aliases": [],
       "standardQuantity": 1.0, "standardUnit": "cup", "createdAt": "2026-04-13", "updatedAt": "2026-04-13"}

# A recipe as Mealie v3.30 returns it, with the nested copies the read tools trim
MEALIE_RECIPE = {
    "id": "1", "userId": "u", "householdId": "h", "groupId": "g",
    "name": "Chili Sauce", "slug": "chili", "image": "abc",
    "recipeServings": 4.0, "recipeYieldQuantity": 0.0, "recipeYield": "",
    "prepTime": None, "prepTimeSeconds": 3600,
    "performTime": None, "performTimeSeconds": 7200,
    "totalTime": None, "totalTimeSeconds": 10800, "cookTime": None,
    "description": "Sweet and spicy.", "rating": None, "orgURL": "https://example.com/chili",
    "recipeCategory": [organizer("Sauce", "sauce")],
    "tags": [organizer("Gluten Free", "gluten-free"), organizer("Spicy", "spicy")],
    "tools": [organizer("Food Processor", "food-processor", householdsWithTool=["allen"])],
    "dateAdded": "2026-01-01", "dateUpdated": "2026-01-02T10:00:00Z",
    "createdAt": "2026-01-01", "updatedAt": "2026-01-02",
    "recipeIngredient": [
        {"quantity": 0.0, "unit": None, "food": None, "referencedRecipe": None, "note": "",
         "display": "", "title": "For the sauce", "originalText": None, "substitutions": [],
         "referenceId": "ref-0"},
        {"quantity": 2.0, "unit": CUP, "food": TOMATO, "referencedRecipe": None, "note": "chopped",
         "display": "2 cups tomato chopped", "title": None, "originalText": None,
         "substitutions": [{"quantity": 1.0, "unit": None, "food": TOMATO, "note": "canned",
                            "display": "1 tomato canned", "referenceId": "ref-1s"}],
         "referenceId": "ref-1"},
        {"quantity": 1.0, "unit": None, "food": None, "note": "pinch of salt", "display": "1 pinch of salt",
         "title": None, "referencedRecipe": None, "substitutions": [], "referenceId": "ref-2"},
        {"quantity": 1.0, "unit": None, "food": None, "note": "", "display": "1 Garlic Paste",
         "title": None, "referencedRecipe": {"id": "r2", "name": "Garlic Paste", "slug": "garlic-paste",
                                             "tags": [organizer("Base", "base")]},
         "substitutions": [], "referenceId": "ref-3"},
    ],
    "recipeInstructions": [
        {"id": "s1", "title": "", "summary": "", "text": "Chop the tomatoes.",
         "ingredientReferences": [{"referenceId": "ref-1"}], "noteReferences": [], "durationSeconds": None},
        {"id": "s2", "title": "Cook", "summary": "", "text": "Simmer.", "ingredientReferences": [],
         "noteReferences": [], "durationSeconds": 600},
    ],
    "nutrition": {"calories": "90", "fatContent": None},
    "settings": {"public": False, "showNutrition": True},
    "assets": [], "notes": [{"title": "Tip", "text": "Keeps a week."}], "extras": {}, "comments": [],
    "futureField": "kept",
}


class FakeRecipes:
    """Stands in for MealieFetcher in the recipe tools."""

    def __init__(self, last_made_error: bool):
        self.last_made_error = last_made_error

    def get_recipe(self, slug):
        return {**json.loads(json.dumps(MEALIE_RECIPE)), "slug": slug}

    def get_recipes(self, **kwargs):
        summary = {k: v for k, v in MEALIE_RECIPE.items()
                   if k not in ("recipeIngredient", "recipeInstructions", "nutrition", "settings",
                                "assets", "notes", "extras", "comments")}
        return {"page": 1, "per_page": 50, "total": 1, "total_pages": 1, "next": None,
                "previous": None, "items": [json.loads(json.dumps(summary))]}

    def get_household_recipe(self, slug):
        if self.last_made_error:
            raise ConnectionError("household lookup failed")
        return {"recipeId": "1", "lastMade": "2026-11-01T18:00:00Z"}


MEATS = {"name": "Meats", "color": "#6D4C41", "groupId": "g", "id": "lab-2"}
POUND = {**CUP, "id": "unit-2", "name": "pound", "pluralName": "pounds", "abbreviation": "lb"}
BEEF = {**TOMATO, "id": "food-2", "name": "ground beef", "labelId": "lab-2", "label": MEATS}


def mealie_item(item_id, **fields):
    """A shopping list item as Mealie returns it (nested objects, internal ids)."""
    return {"quantity": 1.0, "unit": None, "food": None, "referencedRecipe": None, "note": "",
            "display": "", "shoppingListId": "L1", "checked": False, "position": 0, "foodId": None,
            "labelId": None, "unitId": None, "extras": {}, "id": item_id, "groupId": "g",
            "householdId": "h", "label": None, "recipeReferences": [],
            "createdAt": "2026-11-01", "updatedAt": "2026-11-01", **fields}


BEEF_ITEM = mealie_item(
    "I1", quantity=1.0, unit=POUND, food=BEEF, display="1 pound ground beef", foodId="food-2",
    labelId="lab-2", unitId="unit-2", label=MEATS,
    recipeReferences=[{"recipeId": "R1", "recipeQuantity": 1.0, "recipeScale": 1.0, "recipeNote": None,
                       "id": "rr1", "shoppingListItemId": "I1"}])
NOTE_ITEM = mealie_item("I2", note="paper towels", display="1 paper towels", checked=True, position=1)

# A shopping list as Mealie returns it: label settings stored out of position order,
# full recipe summaries in recipeReferences, nested objects in every item
FULL_LIST = {
    "id": "L1", "name": "Groceries", "extras": {}, "groupId": "g", "userId": "u", "householdId": "h",
    "createdAt": "2026-11-01", "updatedAt": "2026-11-01",
    "listItems": [BEEF_ITEM, NOTE_ITEM],
    "labelSettings": [
        {"id": "S1", "shoppingListId": "L1", "labelId": "lab-2", "position": 1, "label": MEATS},
        {"id": "S0", "shoppingListId": "L1", "labelId": "lab-1", "position": 0, "label": LABEL},
    ],
    "recipeReferences": [{
        "id": "ref1", "shoppingListId": "L1", "recipeId": "R1", "recipeQuantity": 2.0,
        "recipe": {"id": "R1", "name": "Chili Sauce", "slug": "chili-sauce",
                   "description": "long text", "tags": [{"name": "t", "recipeCount": 0}]},
    }],
}
TRIMMED_ITEMS = [
    {"id": "I1", "display": "1 pound ground beef", "checked": False, "quantity": 1.0, "unit": "pound",
     "food": "ground beef", "label": "Meats", "recipeIds": ["R1"]},
    {"id": "I2", "display": "1 paper towels", "checked": True, "quantity": 1.0, "note": "paper towels"},
]
TRIMMED_LIST = {
    "id": "L1", "name": "Groceries", "labelOrder": ["Fruits", "Meats"],
    "recipeReferences": [{"recipeId": "R1", "name": "Chili Sauce", "slug": "chili-sauce", "recipeQuantity": 2.0}],
    "listItems": TRIMMED_ITEMS,
}


class FakeShopping:
    """Stands in for MealieFetcher in the shopping list tools; records what it was sent."""

    def __init__(self):
        self.sent = []

    def get_shopping_lists(self, page=None, per_page=None):
        summary = {k: v for k, v in FULL_LIST.items() if k != "listItems"}
        return {"page": 1, "total": 1, "items": [summary]}

    def get_shopping_list_items(self, page=None, per_page=None, search=None):
        return {"page": 1, "per_page": 50, "total": 2, "items": [BEEF_ITEM, NOTE_ITEM]}

    def get_shopping_list_item(self, item_id):
        return BEEF_ITEM

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

    def create_mealplan(self, date, entry_type, recipe_id=None, title=None, whole_week=False):
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

    def update_mealplan(self, entry_id, date, entry_type, recipe_id=None, title=None, whole_week=None):
        entry = next(e for e in self.created if e["id"] == int(entry_id))
        entry.update(date=date, entryType=entry_type)
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
    section("Recipe read tools: trimmed output")
    # ------------------------------------------------------------------
    srv = FastMCP("probe")
    register_recipe_tools(srv, FakeRecipes(last_made_error=False))
    out = call(srv, "get_recipes", {})
    check("get_recipes keeps the pagination fields",
          {k: out.get(k) for k in ("page", "per_page", "total", "total_pages")}
          == {"page": 1, "per_page": 50, "total": 1, "total_pages": 1}, str(out)[:200])
    summary = out["items"][0]
    check("get_recipes: one short card per recipe, in order",
          summary == {
              "id": "1", "name": "Chili Sauce", "slug": "chili", "description": "Sweet and spicy.",
              "tags": ["gluten-free", "spicy"], "recipeCategory": ["sauce"], "tools": ["food-processor"],
              "prepTime": "1 hour", "prepTimeSeconds": 3600, "performTime": "2 hours",
              "performTimeSeconds": 7200, "totalTime": "3 hours", "totalTimeSeconds": 10800,
              "recipeServings": 4.0, "dateAdded": "2026-01-01", "dateUpdated": "2026-01-02T10:00:00Z",
          }, json.dumps(summary))

    d = call(srv, "get_recipe_detailed", {"slug": "chili"})
    dropped = [k for k in ("userId", "groupId", "householdId", "createdAt", "updatedAt", "image",
                           "cookTime", "extras", "settings", "comments", "assets") if k in d]
    check("detailed: internal and duplicate fields dropped", not dropped, str(dropped))
    check("detailed: orgURL, notes, nutrition, lastMade and unknown new fields kept",
          d.get("orgURL") == "https://example.com/chili" and d.get("notes") == MEALIE_RECIPE["notes"]
          and d.get("nutrition") == MEALIE_RECIPE["nutrition"] and d.get("lastMade") == "2026-11-01T18:00:00Z"
          and d.get("futureField") == "kept", str({k: d.get(k) for k in ("orgURL", "lastMade", "futureField")}))
    check("detailed: tags / recipeCategory / tools as slugs",
          (d.get("tags"), d.get("recipeCategory"), d.get("tools"))
          == (["gluten-free", "spicy"], ["sauce"], ["food-processor"]), str(d.get("tags")))
    expected_ingredients = [
        {"title": "For the sauce", "referenceId": "ref-0"},
        {"quantity": 2.0, "note": "chopped", "display": "2 cups tomato chopped", "referenceId": "ref-1",
         "unit": "cup", "food": "tomato", "label": "Fruits",
         "substitutions": [{"quantity": 1.0, "note": "canned", "display": "1 tomato canned",
                            "referenceId": "ref-1s", "food": "tomato", "label": "Fruits"}]},
        {"quantity": 1.0, "note": "pinch of salt", "display": "1 pinch of salt", "referenceId": "ref-2"},
        {"quantity": 1.0, "display": "1 Garlic Paste", "referenceId": "ref-3", "referencedRecipe": "garlic-paste"},
    ]
    check("detailed: ingredients as names (section header, food+unit+label, note-only, sub-recipe)",
          d.get("recipeIngredient") == expected_ingredients, json.dumps(d.get("recipeIngredient")))
    check("detailed: instruction steps without empty fields, links to ingredients kept",
          d.get("recipeInstructions") == [
              {"id": "s1", "text": "Chop the tomatoes.", "ingredientReferences": [{"referenceId": "ref-1"}]},
              {"id": "s2", "title": "Cook", "text": "Simmer.", "durationSeconds": 600},
          ], json.dumps(d.get("recipeInstructions")))

    c = call(srv, "get_recipe_concise", {"slug": "chili"})
    check("concise: name, amounts, totalTime, lastMade and trimmed ingredients",
          c == {"name": "Chili Sauce", "slug": "chili", "recipeServings": 4.0, "totalTime": "3 hours",
                "lastMade": "2026-11-01T18:00:00Z", "recipeIngredient": expected_ingredients}, json.dumps(c))
    everything = json.dumps([out, d, c])
    check("no recipeCount, groupId or nested food/unit objects left in any recipe tool",
          "recipeCount" not in everything and "groupId" not in everything
          and "pluralName" not in everything and "#7CB342" not in everything)
    raw = json.dumps(MEALIE_RECIPE)
    check("trimming leaves Mealie's data untouched",
          json.dumps(FakeRecipes(False).get_recipe("chili")) == json.dumps({**MEALIE_RECIPE, "slug": "chili"})
          and raw == json.dumps(MEALIE_RECIPE))

    # ------------------------------------------------------------------
    section("Shopping list tools trim lists and items")
    # ------------------------------------------------------------------
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
        check(f"{tool}: whole list trimmed (labelOrder, recipeReferences, items)", out == TRIMMED_LIST,
              json.dumps(out)[:200])
    out = call(srv, "get_shopping_lists", {})
    check("get_shopping_lists: each list trimmed, no items (Mealie's summaries have none)",
          out.get("items") == [{k: v for k, v in TRIMMED_LIST.items() if k != "listItems"}]
          and out.get("page") == 1, json.dumps(out)[:200])
    out = call(srv, "get_shopping_list_items", {})
    check("get_shopping_list_items: items trimmed, with their list id, pagination kept",
          out.get("items") == [{**TRIMMED_ITEMS[0], "shoppingListId": "L1"}, {**TRIMMED_ITEMS[1], "shoppingListId": "L1"}]
          and out.get("total") == 2, json.dumps(out)[:200])
    out = call(srv, "get_shopping_list_item", {"item_id": "I1"})
    check("get_shopping_list_item: item trimmed, with its list id",
          out == {**TRIMMED_ITEMS[0], "shoppingListId": "L1"}, json.dumps(out))
    check("no recipeCount, groupId or nested objects left in the shopping list tools",
          not any(k in json.dumps([call(srv, "get_shopping_list", {"list_id": "L1"}),
                                   call(srv, "get_shopping_list_items", {})])
                  for k in ("recipeCount", "groupId", "#6D4C41", "pluralName")))
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
    section("Meal plan create/update: trimmed entries, checks first, partial failures")
    # ------------------------------------------------------------------
    fake = FakeMealplanCreate()
    srv = FastMCP("probe")
    register_mealplan_tools(srv, fake)
    out = call(srv, "create_mealplan", {"date": "2099-03-04", "recipe_id": RECIPE_UUID, "entry_type": "dinner"})
    check("create_mealplan returns the trimmed entry with its id",
          out == {"id": 1, "date": "2099-03-04", "entryType": "dinner", "recipeId": RECIPE_UUID,
                  "recipeName": "Chili Sauce", "recipeSlug": "chili-sauce"}, str(out))
    out = call(srv, "update_mealplan", {"entry_id": 1, "date": "2099-03-05", "entry_type": "lunch"})
    check("update_mealplan returns the trimmed entry",
          out == {"id": 1, "date": "2099-03-05", "entryType": "lunch", "recipeId": RECIPE_UUID,
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
        ("bad date", {"date": "03/06/2099", "title": "x", "entry_type": "dinner"}, "YYYY-MM-DD"),
        ("no recipe or title", {"date": "2099-03-06", "entry_type": "dinner"}, "recipe_id or a title"),
        ("recipe_id not a UUID", {"date": "2099-03-06", "recipe_id": "chili-sauce", "entry_type": "dinner"},
         "not a recipe UUID"),
        ("unknown key", {"date": "2099-03-06", "title": "x", "entryType": "dinner"}, "entryType"),
        ("missing entry_type", {"date": "2099-03-06", "title": "x"}, 'missing "entry_type" (one of: breakfast'),
    ]:
        err = call_error(srv, "create_mealplan_bulk", {"entries": [
            {"date": "2099-03-06", "title": "fine", "entry_type": "dinner"}, entry]})
        check(f"bulk {name}: rejected, names entry 2, nothing created",
              expect in err and "entry 2" in err and "nothing was created" in err
              and len(fake.created) == before, err[-160:])
    err = call_error(srv, "create_mealplan", {"date": "2099-03-06", "title": "x", "entry_type": "brunch"})
    check("create_mealplan rejects a bad entry_type before creating",
          "brunch" in err and len(fake.created) == before, err[-120:])
    err = call_error(srv, "create_mealplan", {"date": "2099-03-06", "title": "x"})
    check("create_mealplan requires entry_type (no breakfast default)",
          "entry_type" in err and len(fake.created) == before, err[-120:])

    err = call_error(srv, "create_mealplan_bulk", {"entries": [
        {"date": "2099-03-08", "title": "a", "entry_type": "dinner"},
        {"date": "2099-03-09", "title": "b", "entry_type": "dinner"},
        {"date": "2099-03-10", "title": "boom", "entry_type": "dinner"},
        {"date": "2099-03-11", "title": "d", "entry_type": "dinner"},
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
