# LLM Integration Test Prompt — WRITE (mutating, cleans up)

⚠️ **This test WRITES to Mealie** — shopping lists, list items and meal plan entries — and
**deletes everything it creates** before it finishes. Every name starts with `__test_llm_` and
every meal plan date is in 2099, so nothing touches real data. Your own shopping lists are not
changed: section order is per list, and only the test list is reordered.

Unlike `LLM_PROMPT.md` (read-only) and `LLM_PROMPT_CREATE.md` (one recipe), this exercises the
shopping list and meal plan **write** tools with a real model: chaining ids between calls,
reordering sections by label name, whole-week entries, and bulk creation including a rejected
batch. Run it after deploying, in each assistant. Paste everything below the line into Claude
or ChatGPT with the Mealie MCP server connected.

---

Using the Mealie MCP server, test the write tools below. Name everything you create with the
prefix `__test_llm_` and delete everything you create before you finish. Do NOT call
create_recipe, duplicate_recipe, create_food, merge_foods, create_recipe_comment,
create_recipe_share_token, or mark_recipe_last_made.

**Shopping lists**
1. create_shopping_list "__test_llm_list"
2. update_shopping_list: rename it to "__test_llm_list_renamed"
3. create_shopping_list_item: note "__test_llm_item"
4. update_shopping_list_item: set checked=true
5. create_shopping_list_items_bulk: two items, notes "__test_llm_bulk_1" and "__test_llm_bulk_2"
6. update_shopping_list_items_bulk: set both bulk items checked=true, sending only each item's id
   and checked → both are checked and their notes are still "__test_llm_bulk_1" / "__test_llm_bulk_2"
7. add_recipe_to_shopping_list: add any existing recipe (pick one from get_recipes with per_page=5)
   → each entry in the returned recipeReferences has exactly recipeId, name, slug and
   recipeQuantity — no embedded recipe
8. remove_recipe_from_shopping_list: remove that recipe again
9. add_recipes_to_shopping_list_bulk: add that same recipe, then remove it again
10. Call get_labels, then get_shopping_list on the test list and note its current section order
    (its labelOrder). Call update_shopping_list_label_settings with the **last three**
    label names of that order, in reverse, spelled exactly as get_labels returns them
    → the returned labelOrder starts with those three, and every other label keeps its previous
    relative order
11. update_shopping_list_label_settings with labels ["__not_a_label__"]
    → must be an error that names "__not_a_label__" and lists the real label names; then
    get_shopping_list → the section order is still exactly the order from step 10
12. delete_shopping_list_item on the single item, delete_shopping_list_items_bulk on the two
    bulk items
13. delete_shopping_list

**Meal plans** (use dates in the year 2099 only)
14. create_mealplan: 2099-03-04, dinner, title "__test_llm_day"
    → the reply has id, date, entryType and title, and no embedded recipe
15. update_mealplan: move it to 2099-03-05, passing entry_id as a **number**, exactly as step 14
    returned it → the reply has id, date 2099-03-05, entryType and title, and no embedded recipe
16. create_mealplan: 2099-03-04, dinner, title "__test_llm_week", whole_week=true
    → report its date and endDate; endDate must be exactly 6 days after date
17. get_all_mealplans with start_date=2099-03-01, end_date=2099-03-31 → both entries are listed
18. update_mealplan on the week entry: date 2099-03-18 (leave whole_week unset)
    → report the new date and endDate; it must still be a 7-day week
19. create_mealplan_bulk with two entries: 2099-03-25 lunch "__test_llm_bulk_a" whole_week=true,
    and 2099-03-26 dinner "__test_llm_bulk_b"
    → the reply lists both under created, in that order, each with an id; bulk_a has an endDate
20. create_mealplan_bulk with two entries: 2099-03-27 lunch "__test_llm_bad_ok", and 2099-03-28
    entry_type "brunch" title "__test_llm_bad"
    → must be an error naming entry 2 and "brunch" and saying nothing was created; then
    get_all_mealplans for 2099-03-01..2099-03-31 → no "__test_llm_bad_ok" entry exists
21. delete_mealplan every `__test_llm_` entry, using the ids the create tools returned in steps
    14, 16 and 19 (no lookup needed). If step 20 created anything, delete that too.
22. get_all_mealplans for 2099-03-01..2099-03-31 again → must be empty

For each step say PASS or FAIL with the tool name; for a FAIL quote the full error or the value
you got. End with: `X/22 passed`, and confirm nothing `__test_llm_` is left.

---

## What a FAIL means
- Step 6: the notes are empty → the bulk update replaced the items instead of merging (on a real
  list this also clears each item's food, quantity and section).
- Step 7: recipeReferences still carry a full `recipe` object → the reference trimming isn't
  deployed.
- Step 10: the call fails asking for ids or positions → the server still takes raw label settings
  (pre-1.0.24). Wrong order → the named-first / rest-unchanged ordering is broken.
- Step 11: the order changed → an unknown name was partly applied instead of rejected.
- Step 15: a schema error about the id's type → `entry_id` doesn't accept a number. A reply with
  groupId, userId or a `recipe` object → the update reply isn't trimmed.
- Step 19: only a message, no ids → bulk create doesn't return the created entries.
- Step 20: "__test_llm_bad_ok" exists → bulk create didn't check every entry before creating.
- Anything `__test_llm_` left over → delete it in the Mealie UI and note which step left it.

## ChatGPT note
Same caveat as `LLM_PROMPT.md`: ChatGPT's safety filter may block some tool calls ("This tool
call was blocked by OpenAI's safety checks"). Treat those as platform noise, not server
failures, and finish the cleanup steps anyway.
