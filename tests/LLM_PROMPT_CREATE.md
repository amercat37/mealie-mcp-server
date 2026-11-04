# LLM Integration Test Prompt — CREATE (mutating)

⚠️ **This test WRITES to Mealie.** It creates exactly one recipe and does **not** delete it —
delete `__test_llm_create__` manually in the Mealie UI when finished. Run it against whatever
instance your MCP client is pointed at (prod is fine; it's one throwaway recipe).

Unlike `LLM_PROMPT.md` (read-only), this test exercises the **write seam that real usage hit**:
a real model choosing field names → `create_recipe` → Mealie → round-trip. It is the acceptance
check that would have caught the "Grandma Mercer's Chili Sauce" silent-field-drop bug.

Best run **after** the create_recipe hardening is deployed, to confirm the fix works end-to-end
with a real LLM. Paste everything below the line into Claude or ChatGPT with the Mealie MCP
server connected.

---

Using the Mealie MCP server, create the following recipe with a **single** `create_recipe` call,
then fetch it back with `get_recipe_detailed` and verify every field round-tripped. Do not invent
values; use exactly what's given.

**Pre-check (before creating):** call `get_units` and report whether a unit named "rashers" (or
"rasher") exists. It should not — ingredient 4 uses it on purpose to test a unit Mealie doesn't know.

**Recipe to create — "__test_llm_create__"**
- Description: "LLM create round-trip test — safe to delete."
- Categories: Sauce, Condiment  *(2 categories)*
- Tags: my-recipes, American
- Tools: Stovetop
- Servings: 4
- Yield: 2 cups  *(quantity 2, bare unit "cups" — no parenthetical text)*
- Prep time: 10 minutes
- Cook time: 20 minutes  *(this must land as the recipe's cook/active time)*
- Total time: 30 minutes
- Ingredients (5):
  1. 2 cups tomato, chopped
  2. 1 cup onion, diced
  3. 3 tablespoons white vinegar
  4. 2 rashers bacon  *(send the unit exactly as "rashers" — do not swap in a catalog unit such as
     "slices"; it is deliberately not in the catalog, and the text must not be lost)*
  5. 1 pinch salt
- Instructions (3):
  1. Combine tomato, onion, and vinegar in a saucepan.
  2. Add the bacon and salt; bring to a boil.
  3. Simmer until thick, stirring so it does not stick.
- Nutrition, **per serving** (bare numbers, no unit suffixes):
  calories 90, carbohydrateContent 12, fatContent 3, proteinContent 2, fiberContent 2,
  sugarContent 7, sodiumContent 150, cholesterolContent 5, saturatedFatContent 1,
  transFatContent 0, unsaturatedFatContent 2

After creating, fetch `get_recipe_detailed` for the new recipe and report **PASS/FAIL for each
group**, quoting the value you got back:

1. name is "__test_llm_create__"
2. **both** categories present (Sauce, Condiment — the tool lists them as slugs: sauce, condiment) ← the bug emptied this
3. **all 5** ingredients present, each with its quantity + food (and unit where given) ← the bug emptied this
4. ingredient 4's unit "rashers" survived in its note — not silently dropped, and not replaced by
   another unit. If the pre-check found "rashers" in the catalog, report this group as
   **NOT TESTED — rashers is now a known unit** instead of PASS
5. **all 3** instructions present, in order              ← the bug emptied this
6. prep / cook / total time all present (cook time not dropped) ← the bug dropped cook time.
   They read back as "10 minutes" / "20 minutes" / "30 minutes" **and** are stored as
   prepTimeSeconds 600 / performTimeSeconds 1200 / totalTimeSeconds 1800
7. servings = 4
8. yield renders as "2 cups" — `recipeYield` is the bare unit "cups", **no parenthetical**
9. all 11 nutrition fields present as **bare numbers** (e.g. "12", not "12 g")

Print a final summary: `X/9 groups passed` (say so if group 4 was NOT TESTED), and list any FAILs
with the actual value returned.

Then **STOP.** Do not delete the recipe — the human will remove `__test_llm_create__` manually.

---

## What a FAIL means
- Empty categories / ingredients / instructions, or missing cook time → the field-name silent-drop
  bug (create_recipe accepted a key it doesn't map and discarded it). Should be impossible once
  `extra="forbid"` + aliases are deployed.
- Times readable but a *TimeSeconds field missing → create_recipe stored the time as legacy text
  instead of Mealie's structured duration (Mealie v3.29+), so time filters and sorting skip it.
- "rashers" missing entirely → the unknown-unit path dropped it instead of preserving it in the note.
- "rashers" replaced by "slices" (or another unit) → the model substituted a catalog unit instead of
  sending what was given, so the unknown-unit path wasn't exercised.
- Group 4 NOT TESTED → someone added "rashers" to the unit catalog; pick another real unit that
  isn't in `get_units` (the test needs one Mealie doesn't know).
- `recipeYield` contains a parenthetical, or nutrition values carry unit suffixes → the model
  ignored content guidance (a validator, not just the prompt, is what guarantees these).

## ChatGPT note
Same read-only false-positive caveat as `LLM_PROMPT.md` may apply to the get calls; the
`create_recipe` call itself is the point of this test.
