"""
Script 5: RecipeCreate model unit tests (create_recipe silent-field-drop fix).

No live infrastructure — validates the Pydantic model + FastMCP tool schema/error
behavior directly. Locks in the fix for the bug where create_recipe silently dropped
fields whose key didn't match the model (categories/ingredients/instructions/cookTime).

Usage:
    cd mealie-mcp-server
    python tests/test_recipe_model.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pydantic import ValidationError

from models.recipe import RecipeCreate, RecipeNutritionCreate
from recipe_times import BareNumberError, add_readable_times, format_duration, parse_duration

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, bool(condition), detail))


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def run() -> None:
    # ------------------------------------------------------------------
    section("Aliases map natural names -> Mealie fields")
    # ------------------------------------------------------------------
    m = RecipeCreate.model_validate({
        "name": "x",
        "categories": ["sauce"],
        "ingredients": [{"food": "tomato", "quantity": 2, "unit": "cup"}],
        "instructions": [{"text": "boil"}],
        "cookTime": "20 minutes",
        "servings": 4,
        "sourceUrl": "https://example.com/r",
    })
    check("categories -> recipeCategory", m.recipeCategory == ["sauce"], str(m.recipeCategory))
    check("ingredients -> recipeIngredient", len(m.recipeIngredient) == 1 and m.recipeIngredient[0].food == "tomato")
    check("instructions -> recipeInstructions", len(m.recipeInstructions) == 1 and m.recipeInstructions[0].text == "boil")
    check("cookTime -> performTime", m.performTime == "20 minutes", str(m.performTime))
    check("servings -> recipeServings", m.recipeServings == 4, str(m.recipeServings))
    check("sourceUrl -> orgURL", m.orgURL == "https://example.com/r", str(m.orgURL))

    # 'url' is also an alias for orgURL
    m2 = RecipeCreate.model_validate({"name": "x", "url": "https://ex.com"})
    check("url -> orgURL", m2.orgURL == "https://ex.com", str(m2.orgURL))

    # ------------------------------------------------------------------
    section("Canonical (exact Mealie) names still work")
    # ------------------------------------------------------------------
    mc = RecipeCreate.model_validate({
        "name": "x",
        "recipeCategory": ["sauce"],
        "recipeIngredient": [{"food": "tomato"}],
        "recipeInstructions": [{"text": "boil"}],
        "performTime": "20 minutes",
        "recipeServings": 4,
        "orgURL": "https://ex.com",
    })
    check("canonical recipeCategory", mc.recipeCategory == ["sauce"])
    check("canonical performTime", mc.performTime == "20 minutes")
    check("canonical recipeServings", mc.recipeServings == 4)

    # ------------------------------------------------------------------
    section("extra='forbid' fails loud on unknown keys (no silent drop)")
    # ------------------------------------------------------------------
    def expect_forbidden(label, data, loc_contains):
        try:
            RecipeCreate.model_validate(data)
            check(label, False, "no error raised (silent accept!)")
        except ValidationError as e:
            types_ = {er["type"] for er in e.errors()}
            locs = [er["loc"] for er in e.errors()]
            ok = "extra_forbidden" in types_ and any(loc_contains in str(l) for l in locs)
            check(label, ok, f"types={types_} locs={locs}")

    expect_forbidden("unknown top-level key 'steps'", {"name": "x", "steps": ["a"]}, "steps")
    expect_forbidden("nested ingredient wrong key {amount}",
                     {"name": "x", "recipeIngredient": [{"amount": 5}]}, "amount")
    expect_forbidden("nested instruction wrong key {step}",
                     {"name": "x", "recipeInstructions": [{"step": "boil"}]}, "step")
    expect_forbidden("nested nutrition wrong key {carbs}",
                     {"name": "x", "nutrition": {"carbs": "12"}}, "carbs")
    # instruction requires 'text' — omitting it must error too (not silently create empty)
    try:
        RecipeCreate.model_validate({"name": "x", "recipeInstructions": [{"title": "t"}]})
        check("instruction missing required 'text' errors", False, "no error")
    except ValidationError as e:
        check("instruction missing required 'text' errors",
              any(er["type"] == "missing" for er in e.errors()))

    # ------------------------------------------------------------------
    section("Nutrition values normalize to bare numbers")
    # ------------------------------------------------------------------
    n = RecipeNutritionCreate.model_validate({
        "calories": "90", "carbohydrateContent": "4.9 g", "sodiumContent": "1,200 mg",
        "fatContent": "0.5g", "fiberContent": "<1 g", "proteinContent": "trace",
    })
    check("bare number unchanged (90)", n.calories == "90", n.calories)
    check("'4.9 g' -> '4.9'", n.carbohydrateContent == "4.9", n.carbohydrateContent)
    check("'1,200 mg' -> '1200' (comma handled)", n.sodiumContent == "1200", n.sodiumContent)
    check("'0.5g' -> '0.5'", n.fatContent == "0.5", n.fatContent)
    check("'<1 g' -> '1'", n.fiberContent == "1", n.fiberContent)
    check("'trace' preserved", n.proteinContent == "trace", n.proteinContent)

    # ------------------------------------------------------------------
    section("model_dump produces canonical Mealie keys (for the PATCH)")
    # ------------------------------------------------------------------
    dumped = m.model_dump(exclude_none=True)
    check("dump uses 'recipeCategory' not 'categories'",
          "recipeCategory" in dumped and "categories" not in dumped)
    check("dump uses 'performTime' not 'cookTime'",
          "performTime" in dumped and "cookTime" not in dumped)
    nd = n.model_dump(exclude_none=True)
    check("nutrition dump values are bare numbers",
          nd.get("carbohydrateContent") == "4.9" and nd.get("sodiumContent") == "1200")

    # ------------------------------------------------------------------
    section("Recipe times: parse text -> seconds")
    # ------------------------------------------------------------------
    for text, expected in [
        ("30 minutes", 1800), ("1 minute", 60), ("1 hour", 3600), ("3 hours", 10800),
        ("2 hours 45 minutes", 9900), ("1 hour and 30 minutes", 5400), ("1 hour, 30 minutes", 5400),
        ("90 min", 5400), ("1.5 hrs", 5400), ("1h30m", 5400), ("2 days", 172800),
        ("PT1H30M", 5400), ("pt45m", 2700), ("  20 Minutes ", 1200), ("0 minutes", 0),
    ]:
        got = parse_duration(text)
        check(f"parse {text!r} -> {expected}", got == expected, str(got))
    for text in ["overnight", "about 20 minutes", "30 minutes plus chilling", "varies",
                 "30 minutes 1 hour", "1 hour 1 hour", "0.5 seconds", "", None]:
        got = parse_duration(text)
        check(f"parse {text!r} -> None (not a duration)", got is None, str(got))
    for text in ["45", "3", "1.5"]:
        try:
            parse_duration(text)
            check(f"parse {text!r} rejected (no unit)", False, "no error")
        except BareNumberError as e:
            check(f"parse {text!r} rejected (no unit)", "no unit" in str(e), str(e))

    # ------------------------------------------------------------------
    section("Recipe times: seconds -> readable text")
    # ------------------------------------------------------------------
    for seconds, expected in [(60, "1 minute"), (1800, "30 minutes"), (3600, "1 hour"),
                              (5400, "1 hour 30 minutes"), (10800, "3 hours"),
                              (90000, "1 day 1 hour")]:
        check(f"format {seconds} -> {expected!r}", format_duration(seconds) == expected,
              format_duration(seconds))
    r = add_readable_times({"prepTime": None, "prepTimeSeconds": 3600,
                            "performTime": "overnight", "performTimeSeconds": None,
                            "totalTime": None, "totalTimeSeconds": None})
    check("readable from seconds", r["prepTime"] == "1 hour" and r["prepTimeSeconds"] == 3600, str(r))
    check("text-only time kept as-is", r["performTime"] == "overnight", str(r))
    check("no time stays empty", r["totalTime"] is None, str(r))

    # ------------------------------------------------------------------
    section("Recipe times: create_recipe stores seconds (time_patch)")
    # ------------------------------------------------------------------
    tp = RecipeCreate.model_validate({
        "name": "x", "prepTime": "10 minutes", "cookTime": "1 hour 30 minutes",
        "totalTime": "overnight",
    }).time_patch()
    check("text durations stored as seconds only",
          tp.get("prepTimeSeconds") == 600 and tp.get("performTimeSeconds") == 5400
          and "prepTime" not in tp and "performTime" not in tp, str(tp))
    check("non-duration stored as text only",
          tp.get("totalTime") == "overnight" and "totalTimeSeconds" not in tp, str(tp))
    tp = RecipeCreate.model_validate({
        "name": "x", "prepTimeSeconds": 900, "cookTimeSeconds": 1200,
        "totalTime": "35 minutes", "totalTimeSeconds": 2100,
    }).time_patch()
    check("*Seconds accepted (incl. cookTimeSeconds alias); seconds win over text",
          tp == {"prepTimeSeconds": 900, "performTimeSeconds": 1200, "totalTimeSeconds": 2100}, str(tp))
    tp = RecipeCreate.model_validate({"name": "x", "performTime": "0 minutes",
                                      "totalTimeSeconds": 0}).time_patch()
    check("zero time stored as no time", tp == {}, str(tp))
    try:
        RecipeCreate.model_validate({"name": "x", "prepTime": "45"})
        check("bare-number time rejected at validation", False, "no error")
    except ValidationError as e:
        check("bare-number time rejected at validation", "no unit" in str(e), str(e)[:120])
    try:
        RecipeCreate.model_validate({"name": "x", "prepTimeSeconds": -5})
        check("negative seconds rejected", False, "no error")
    except ValidationError:
        check("negative seconds rejected", True)

    # ------------------------------------------------------------------
    section("FastMCP tool schema + isError behavior")
    # ------------------------------------------------------------------
    try:
        import asyncio
        from mcp.server.fastmcp import FastMCP

        srv = FastMCP("probe")

        @srv.tool()
        def create_recipe(recipe: RecipeCreate) -> dict:
            return {"ok": True}

        async def _schema():
            tools = await srv.list_tools()
            return tools[0].inputSchema

        schema = asyncio.run(_schema())
        rc = schema["$defs"]["RecipeCreate"]
        check("tool schema: additionalProperties false", rc.get("additionalProperties") is False, str(rc.get("additionalProperties")))
        check("tool schema advertises canonical 'recipeCategory'", "recipeCategory" in rc["properties"])
        check("tool schema does NOT advertise alias 'categories'", "categories" not in rc["properties"])

        async def _call(args):
            return await srv.call_tool("create_recipe", args)

        # good alias call succeeds
        try:
            asyncio.run(_call({"recipe": {"name": "x", "categories": ["sauce"]}}))
            check("FastMCP accepts alias call", True)
        except Exception as e:
            check("FastMCP accepts alias call", False, repr(e))

        # bad call raises (server layer converts to isError:true — verified in mcp source)
        try:
            asyncio.run(_call({"recipe": {"name": "x", "steps": ["a"]}}))
            check("FastMCP rejects unknown key", False, "no exception")
        except Exception as e:
            msg = str(e)
            check("FastMCP rejects unknown key with extra_forbidden msg",
                  "extra_forbidden" in msg or "Extra inputs are not permitted" in msg, msg[:120])
    except ImportError as e:
        check("FastMCP schema tests", False, f"mcp not importable: {e}")

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
