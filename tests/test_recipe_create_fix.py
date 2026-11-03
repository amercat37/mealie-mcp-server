"""
Script 6: create_recipe hardening — end-to-end integration test.

Exercises the silent-field-drop fix through the real MCP protocol against a running
server (the throwaway `tests/docker-compose.yml` is fine). Complements the
deterministic model tests (`test_recipe_model.py`) by proving the behavior end-to-end:
alias field names + name-not-slug organizers round-trip, nutrition units are stripped,
and an unknown key returns an isError result instead of silently creating a stub.

Self-cleaning: deletes its `__test_fix_*` recipes at the end.

Usage:
    cd mealie-mcp-server
    docker compose -f tests/docker-compose.yml up -d --build
    python tests/test_recipe_create_fix.py
"""

import asyncio
import json
import os
import sys

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env.testing"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mealie import MealieFetcher

try:
    from mcp.client.streamable_http import streamablehttp_client
    from mcp import ClientSession
except ImportError:
    print("ERROR: mcp package not found."); sys.exit(1)

_mealie = MealieFetcher(base_url=os.environ["MEALIE_BASE_URL"], api_key=os.environ["MEALIE_API_KEY"])

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    print(f"  [{PASS if condition else FAIL}] {name}" + (f" — {detail}" if detail else ""))
    results.append((name, bool(condition), detail))


def section(title: str) -> None:
    print(f"\n{'='*60}\n  {title}\n{'='*60}")


def _text(res):
    return res.content[0].text if res.content else ""


async def run(session) -> int:
    slugs_to_clean = ["test-fix-friendly", "test-fix-bad", "test-fix-nameslug"]
    for s in slugs_to_clean:
        try:
            _mealie.delete_recipe(s)
        except Exception:
            pass

    # ------------------------------------------------------------------
    section("Alias field names + name-not-slug organizer round-trip end-to-end")
    # ------------------------------------------------------------------
    # Send the NATURAL names a real LLM tends to emit (categories/ingredients/
    # instructions/cookTime/servings) AND a category as a display NAME ("Sauce")
    # rather than a slug — all of which silently vanished before the fix.
    payload = {
        "recipe": {
            "name": "__test_fix_friendly__",
            "categories": ["Sauce", "Condiment"],       # alias + NAME not slug
            "tags": ["my-recipes"],
            "ingredients": [                              # alias
                {"quantity": 2, "unit": "cup", "food": "tomato", "note": "chopped"},
                {"quantity": 1, "unit": "pinch", "food": "salt"},
            ],
            "instructions": [{"text": "Combine and simmer."}, {"text": "Jar it."}],  # alias
            "cookTime": "20 minutes",                    # alias -> performTime
            "servings": 4,                               # alias -> recipeServings
            "recipeYieldQuantity": 2,
            "recipeYield": "cups",
            "nutrition": {"calories": "90", "carbohydrateContent": "12 g", "sodiumContent": "1,200 mg"},
        }
    }
    try:
        r = await session.call_tool("create_recipe", payload)
        check("create with alias/name-not-slug did not error", not r.isError, _text(r)[:120])
    except Exception as e:
        check("create with alias/name-not-slug did not error", False, repr(e))

    try:
        d = await session.call_tool("get_recipe_detailed", {"slug": "test-fix-friendly"})
        rec = json.loads(_text(d))
        cats = {c.get("slug") for c in rec.get("recipeCategory", [])}
        ings = rec.get("recipeIngredient", [])
        instrs = rec.get("recipeInstructions", [])
        nut = rec.get("nutrition", {})
        check("both categories resolved from NAMES (Sauce/Condiment)",
              {"sauce", "condiment"} <= cats, str(cats))
        check("all ingredients present (alias 'ingredients')", len(ings) == 2, f"{len(ings)}")
        check("all instructions present (alias 'instructions')", len(instrs) == 2, f"{len(instrs)}")
        check("cookTime landed in performTime", rec.get("performTime") == "20 minutes", str(rec.get("performTime")))
        check("servings -> recipeServings", rec.get("recipeServings") == 4, str(rec.get("recipeServings")))
        check("yield bare unit preserved", rec.get("recipeYield") == "cups", str(rec.get("recipeYield")))
        check("nutrition '12 g' stored as bare '12'", nut.get("carbohydrateContent") == "12", str(nut.get("carbohydrateContent")))
        check("nutrition '1,200 mg' stored as bare '1200'", nut.get("sodiumContent") == "1200", str(nut.get("sodiumContent")))
    except Exception as e:
        check("readback/verify friendly recipe", False, repr(e))

    # ------------------------------------------------------------------
    section("Unknown key fails loud (isError), not a silent stub")
    # ------------------------------------------------------------------
    try:
        r = await session.call_tool("create_recipe", {"recipe": {"name": "__test_fix_bad__", "steps": ["x"]}})
        txt = _text(r)
        check("unknown key 'steps' returns isError", r.isError is True, f"isError={r.isError}")
        check("error message names the offending field / extra_forbidden",
              "steps" in txt or "extra_forbidden" in txt or "Extra inputs" in txt, txt[:120])
        # And it must NOT have created a stub recipe
        made = False
        try:
            _mealie.get_recipe("test-fix-bad")
            made = True
        except Exception:
            made = False
        check("no stub recipe created on rejected call", not made, "stub was created!" if made else "")
    except Exception as e:
        check("unknown key 'steps' returns isError", False, repr(e))

    # ------------------------------------------------------------------
    section("Cleanup")
    # ------------------------------------------------------------------
    for s in slugs_to_clean:
        try:
            _mealie.delete_recipe(s)
            check(f"cleanup delete_recipe ({s})", True)
        except Exception:
            pass  # some (e.g. test-fix-bad) were never created — fine

    section("Summary")
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n  {passed}/{len(results)} passed", end="")
    if failed:
        print(f"  ({failed} failed)\n\nFailed:")
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
        sys.exit(1)


if __name__ == "__main__":
    # Exit after main() returns: a SystemExit raised inside the MCP client's async
    # context managers is wrapped in a BaseExceptionGroup, so even a fully passing
    # run exited with code 1.
    sys.exit(0 if asyncio.run(main()) == 0 else 1)
