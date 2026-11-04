# LLM Integration Test Prompt — WRITE (mutating, cleans up)

⚠️ **This test WRITES to Mealie** — shopping lists, list items and meal plan entries — and
**deletes everything it creates** before it finishes. Every name starts with `__test_llm_` and
every meal plan date is in 2099, so nothing touches real data. Your own shopping lists are not
changed: section order is per list, and only the test list is reordered.

Unlike `LLM_PROMPT.md` (read-only) and `LLM_PROMPT_CREATE.md` (one recipe), this exercises the
shopping list and meal plan **write** tools with a real model: chaining ids between calls,
an item merging into an existing line, reordering sections by label name, a delete with a
made-up id, whole-week entries, and bulk creation including a rejected batch. Run it after deploying, in each assistant. Paste everything below the line into Claude
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
   → the reply has `created` with that item (id, display, checked false) and no `updated`
4. create_shopping_list_item again with the same note "__test_llm_item"
   → the reply has `updated` (not `created`) with the **same id** as step 3 and quantity 2: Mealie
   adds to a matching line instead of making a second one
5. update_shopping_list_item: set checked=true → the reply has `updated` with checked true
6. create_shopping_list_items_bulk: two items, notes "__test_llm_bulk_1" and "__test_llm_bulk_2"
7. update_shopping_list_items_bulk: set both bulk items checked=true, sending only each item's id
   and checked → both are checked and their notes are still "__test_llm_bulk_1" / "__test_llm_bulk_2"
8. add_recipe_to_shopping_list: add any existing recipe (pick one from get_recipes with per_page=5)
   → each entry in the returned recipeReferences has exactly recipeId, name, slug and
   recipeQuantity — no embedded recipe; the list's items give food, unit and label as plain names
9. remove_recipe_from_shopping_list: remove that recipe again
10. add_recipes_to_shopping_list_bulk: add that same recipe, then remove it again
11. Call get_labels, then get_shopping_list on the test list and note its current section order
    (its labelOrder). Call update_shopping_list_label_settings with the **last three**
    label names of that order, in reverse, spelled exactly as get_labels returns them
    → the returned labelOrder starts with those three, and every other label keeps its previous
    relative order
12. update_shopping_list_label_settings with labels ["__not_a_label__"]
    → must be an error that names "__not_a_label__" and lists the real label names; then
    get_shopping_list → the section order is still exactly the order from step 11
13. delete_shopping_list_items_bulk with "__test_llm_bulk_1"'s id **and** the made-up id
    "00000000-0000-4000-8000-000000000000"
    → must be an error naming the made-up id and saying nothing was deleted; then
    get_shopping_list → "__test_llm_bulk_1" is still on the list
14. delete_shopping_list_item on "__test_llm_item", then delete_shopping_list_items_bulk on the two
    bulk items → each reply has `deleted` listing the removed items by display text
15. delete_shopping_list → the reply has `deleted` with the list's id, name and itemCount

**Meal plans** (use dates in the year 2099 only)
16. create_mealplan: 2099-03-04, dinner, title "__test_llm_day"
    → the reply has id, date, entryType and title, and no embedded recipe
17. update_mealplan: move it to 2099-03-05, passing entry_id as a **number**, exactly as step 16
    returned it → the reply has id, date 2099-03-05, entryType and title, and no embedded recipe
18. create_mealplan: 2099-03-04, dinner, title "__test_llm_week", whole_week=true
    → report its date and endDate; endDate must be exactly 6 days after date
19. get_all_mealplans with start_date=2099-03-01, end_date=2099-03-31 → both entries are listed,
    each as a short card (id, date, entryType, title; endDate on the week entry) with no
    embedded recipe and no groupId/userId
20. update_mealplan on the week entry: date 2099-03-18 (leave whole_week unset)
    → report the new date and endDate; it must still be a 7-day week
21. create_mealplan_bulk with two entries: 2099-03-25 lunch "__test_llm_bulk_a" whole_week=true,
    and 2099-03-26 dinner "__test_llm_bulk_b"
    → the reply lists both under created, in that order, each with an id; bulk_a has an endDate
22. create_mealplan_bulk with two entries: 2099-03-27 lunch "__test_llm_bad_ok", and 2099-03-28
    entry_type "brunch" title "__test_llm_bad"
    → must be an error naming entry 2 and "brunch" and saying nothing was created; then
    get_all_mealplans for 2099-03-01..2099-03-31 → no "__test_llm_bad_ok" entry exists
23. delete_mealplan every `__test_llm_` entry, using the ids the create tools returned in steps
    16, 18 and 21 (no lookup needed). If step 22 created anything, delete that too.
    → each reply has `deleted` with that entry's card (its title)
24. get_all_mealplans for 2099-03-01..2099-03-31 again → must be empty

For each step say PASS or FAIL with the tool name; for a FAIL quote the full error or the value
you got. End with: `X/24 passed`, and confirm nothing `__test_llm_` is left.

---

## What a FAIL means
- Step 3–5: Mealie's raw reply (`createdItems` / `updatedItems` / `deletedItems`, full food and
  unit objects) → the item replies aren't trimmed (pre-1.0.25). Step 4 shows `created` with a new
  id → a second line was made instead of a merge (check the list).
- Step 7: the notes are empty → the bulk update replaced the items instead of merging (on a real
  list this also clears each item's food, quantity and section).
- Step 8: recipeReferences still carry a full `recipe` object, or items carry food/unit/label
  objects → the list trimming isn't deployed.
- Step 11: the call fails asking for ids or positions → the server still takes raw label settings
  (pre-1.0.24). Wrong order → the named-first / rest-unchanged ordering is broken.
- Step 12: the order changed → an unknown name was partly applied instead of rejected.
- Step 13: "__test_llm_bulk_1" is gone, or the call "succeeded" → the delete didn't check the ids
  first (Mealie itself reports success for any id).
- Step 14/15/23: `{"message": "", "error": false}`, the whole list, or a full entry → the delete
  replies aren't trimmed (pre-1.0.25).
- Step 17: a schema error about the id's type → `entry_id` doesn't accept a number. A reply with
  groupId, userId or a `recipe` object → the update reply isn't trimmed.
- Step 19: entries carry a `recipe` object or groupId → the meal plan reads aren't trimmed.
- Step 21: only a message, no ids → bulk create doesn't return the created entries.
- Step 22: "__test_llm_bad_ok" exists → bulk create didn't check every entry before creating.
- Anything `__test_llm_` left over → delete it in the Mealie UI and note which step left it.

## ChatGPT note
Same caveat as `LLM_PROMPT.md`: ChatGPT's safety filter may block some tool calls ("This tool
call was blocked by OpenAI's safety checks"). Treat those as platform noise, not server
failures, and finish the cleanup steps anyway.
