# Usage Examples

Practical examples for using the Mealie MCP Server with Claude and ChatGPT.

## Table of Contents

- [Server Prompts](#server-prompts)
- [Recipe Tools](#recipe-tools)
- [Shopping List Tools](#shopping-list-tools)
- [Category Tools](#category-tools)
- [Tag Tools](#tag-tools)
- [Food Tools](#food-tools)
- [Meal Plan Tools](#meal-plan-tools)
- [Cookbook Tools](#cookbook-tools)
- [Organizer Tools](#organizer-tools)
- [Workflows](#workflows)

---

## Server Prompts

MCP prompts are pre-built conversation starters that inject system instructions and context into the AI assistant before the conversation begins. Unlike regular chat messages, prompts configure how the assistant approaches a task — what tools to use, in what order, and how to present results.

### weekly_meal_plan

**What it does:** Starts a guided meal planning session. The assistant pulls your full Mealie recipe library, builds a multi-day plan using your meal categories, applies tag filters and dietary notes, handles leftover reuse, enforces sandwich rules, and saves the confirmed plan to Mealie.

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `days` | `7` | Number of days to plan |
| `tags` | _(empty)_ | Comma-separated tag slugs to filter recipes (empty = all recipes) |
| `meals` | `Breakfast,Lunch,Dinner,Side Dish,Snack,Dessert` | Meal categories per day |
| `notes` | _(empty)_ | Strict dietary notes or constraints |

**Examples:**
```
days=7, tags="", meals="Breakfast,Lunch,Dinner", notes=""
days=5, tags="weeknight", meals="Dinner,Side Dish", notes="no pork"
days=7, tags="gluten-free", notes="nut allergy, avoid tree nuts"
```

**What happens behind the scenes:**
1. Assistant fetches all recipes from your Mealie database
2. Applies tag filters if specified
3. Builds a plan matching your meal categories to Mealie recipe categories
4. Presents the plan in table format and asks for any swaps
5. After confirmation, saves the plan to Mealie

---

### shopping_trip

**What it does:** Builds a consolidated shopping list from your current meal plan, grouped by grocery store section labels, with a cost estimate using Aldi/Price Rite pricing.

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `store` | _(empty)_ | Store name to optimize label order for (e.g. "Kroger", "Aldi") |
| `notes` | _(empty)_ | Additional exclusions or notes |

**Examples:**
```
store="Aldi", notes=""
store="Kroger", notes="skip pantry staples I already have"
store="", notes="exclude spices, I have them all"
```

---

### cooking_session

**What it does:** Stages everything you need before starting to cook — full recipe details, required equipment, units, and any existing cooking notes/comments. Works from a specific recipe or today's meal plan.

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `recipe` | _(empty)_ | Recipe name or slug (empty = use today's meal plan) |

**Examples:**
```
recipe="lasagna"
recipe="chicken-parmesan"
recipe=""  → assistant asks which of today's meals you're cooking
```

---

### weekly_review

**What it does:** Summarizes your cooking and eating history over a time period using the recipe timeline and meal plan history. Answers questions like "what did I eat last Wednesday?" or "what have I been making lately?"

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `period` | `"this week"` | Time period to review |

**Examples:**
```
period="this week"
period="last week"
period="last 30 days"
period="last Wednesday"
```

---

### nutrition_summary

**What it does:** Calculates caloric and macro intake (calories, carbs, fat, protein, fiber, sodium, sugar) from your meal plan's nutrition data. Flags any recipes missing nutrition info rather than silently returning zeros.

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `period` | `"today"` | Time period to calculate |

**Examples:**
```
period="today"
period="this week"
period="Monday"
```

> **Note:** Output quality depends on whether your recipes have nutrition data filled in. Recipes added manually without nutrition info will be flagged.

---

### recipe_builder

**What it does:** Guides the creation of a new recipe in Mealie using your existing conventions. Fetches 2-3 similar recipes first to observe how you use categories, tags, and tools — then follows those patterns exactly. Matches ingredients to your existing food library before creating new ones. New foods get a shopping list label (aisle) assigned. Defaults to the "My Recipes" cookbook.

**Parameters:**

| Parameter | Default | Description |
|---|---|---|
| `name` | _(empty)_ | Recipe name if already known |
| `source` | _(empty)_ | Where the recipe comes from (website, cookbook, memory) |
| `cookbook` | `"my-recipes"` | Cookbook tag to assign — `"my-recipes"` or `"the-autoimmune-solution"` |

**Examples:**
```
name="Beef Stew", source="from memory"
name="Banana Bread", source="King Arthur Flour website", cookbook="my-recipes"
cookbook="the-autoimmune-solution"
```

**What happens behind the scenes:**
1. Fetches 2-3 similar recipes to learn your category/tag/tool patterns
2. Gathers all recipe fields conversationally
3. Fuzzy-matches each ingredient to the food library — reuses existing foods by exact name
4. For new foods, fetches labels and assigns the right shopping list aisle
5. Presents a full recipe-card preview for confirmation
6. On confirmation: creates any missing foods, then POSTs + PATCHes the full recipe

---

## Recipe Tools

### get_recipes — GET /api/recipes

Lists and searches recipes with optional filtering. Always use slugs when filtering by tag or category, not display names.

```
"Show me all my recipes"
"Search for chicken recipes"
"Find recipes with 'pasta' in the name"
"Show me 50 recipes"
```

**Filtering by category (use slugs):**
```
"Get all breakfast recipes"         → category slug: breakfast
"Find recipes in the dinner category" → category slug: dinner
"Show me side dish recipes"         → category slug: side-dish
```

**Filtering by tag:**
```
"Find recipes tagged 'quick'"
"Show me recipes with both 'healthy' AND 'vegetarian' tags"
"Find recipes tagged 'quick' OR 'easy'"
```

**Combined filters:**
```
"Find quick chicken dinner recipes"
"Show me healthy breakfast recipes tagged 'easy'"
```

---

### get_recipe_detailed — GET /api/recipes/{slug}

Returns the full recipe including all ingredients with quantities and units, step-by-step instructions, nutrition info, notes, assets, and metadata. Use this when you need everything — cooking, nutrition calculation, sharing.

```
"Show me the full lasagna recipe"
"Get all the details for chicken parmesan"
"Show me the complete instructions for beef stew"
```

---

### get_recipe_concise — GET /api/recipes/{slug}

Returns a compact recipe summary — name, servings, total time, rating, ingredients list, and last made date. Use this during meal planning or quick lookups to avoid large responses.

```
"Give me a quick summary of the lasagna recipe"
"What are the ingredients and servings for chicken soup?"
"How long does the pasta recipe take?"
```

> **When to use which:** Use `get_recipe_concise` when planning meals or building lists. Use `get_recipe_detailed` when you're about to cook, sharing, or calculating nutrition.

---

### mark_recipe_last_made — PATCH /api/recipes/{slug}/last-made

Updates the last made timestamp on a recipe to today's date.

```
"Mark the chicken parmesan as made today"
"Update the last made date for lasagna"
"I just made the beef stew — mark it as made"
```

---

### get_recipe_comments — GET /api/recipes/{slug}/comments

Returns all comments on a recipe. Comments are used as cooking notes — tips, substitutions, timing adjustments.

```
"Show me the cooking notes for lasagna"
"What comments are on the chicken soup recipe?"
"Have I left any notes on the beef stew?"
```

---

### create_recipe_comment — POST /api/recipes/{slug}/comments

Posts a comment on a recipe. Use this to record what worked, what didn't, or any adjustments you made.

```
"Add a note to lasagna: used half the salt, was perfect"
"Comment on chicken parmesan: cooked 5 minutes longer, still juicy"
"Note on beef stew: added an extra potato, family loved it"
```

---

### get_recipe_timeline — GET /api/recipes/timeline

Returns a chronological activity feed across all recipes. Use this to see what you've been cooking lately or to answer date-specific questions.

```
"What have I been cooking lately?"
"Show me my recent recipe activity"
"What recipes have I made this month?"
```

---

### get_recipe_share_tokens — GET /api/recipes/{slug}/share

Lists existing public share links for a recipe.

```
"Show me the share links for lasagna"
"Do I have any existing share links for chicken parmesan?"
```

---

### create_recipe_share_token — POST /api/recipes/{slug}/share

Creates a new public share link for a recipe. Share it with anyone — they don't need a Mealie account.

```
"Create a share link for the lasagna recipe"
"Generate a shareable link for chicken soup so I can text it to my mom"
"Share the beef stew recipe"
```

---

### get_recipe_exports — GET /api/recipes/{slug}/exports

Returns available export formats and download links for a recipe, including a PDF link.

```
"Get the PDF link for the lasagna recipe"
"Show me export options for chicken parmesan"
"Get a downloadable link for the beef stew recipe"
```

---

### create_recipe — POST /api/recipes + PATCH /api/recipes/{slug}

Creates a fully structured recipe in one call. Resolves category/tag/tool slugs to full objects and matches food names to the library automatically. Use the `recipe_builder` prompt for guided creation.

```
"Add a new recipe: Beef Stew — serves 6, 3 hours, categories: Dinner, Soup"
"Create a recipe called Green Smoothie with spinach, banana, almond milk, and honey"
"Add the autoimmune solution chicken recipe"
```

> **Tip:** Always let the assistant fetch existing similar recipes first so it can match your category/tag conventions. New foods are created automatically if they don't exist in the library.

---

### duplicate_recipe — POST /api/recipes/{slug}/duplicate

Clones an existing recipe under a new name. Use this before making significant variations so the original stays untouched.

```
"Duplicate the beef stew recipe as a vegetarian version"
"Clone chicken tikka masala and call it a slow cooker version"
"Make a copy of the banana bread recipe so I can scale it up"
```

---

## Shopping List Tools

### get_shopping_lists — GET /api/households/shopping/lists

Returns all shopping lists for the household.

```
"Show me all my shopping lists"
"What shopping lists do I have?"
"List all my grocery lists"
```

---

### create_shopping_list — POST /api/households/shopping/lists

Creates a new empty shopping list.

```
"Create a shopping list called 'Weekly Groceries'"
"Make a new list called 'Thanksgiving Shopping'"
"Start a new shopping list for this week"
```

---

### get_shopping_list — GET /api/households/shopping/lists/{id}

Returns a specific shopping list and all its items by ID.

```
"Show me my Weekly Groceries list"
"What's on my Thanksgiving shopping list?"
"Get the details of my grocery list"
```

---

### update_shopping_list — PUT /api/households/shopping/lists/{id}

Renames an existing shopping list.

```
"Rename my shopping list to 'Kroger Run'"
"Change the list name from 'Weekly' to 'Weekly Groceries'"
```

---

### delete_shopping_list — DELETE /api/households/shopping/lists/{id}

Permanently deletes a shopping list and all its items.

```
"Delete my old shopping list"
"Remove the Thanksgiving list"
"Get rid of my Weekly Groceries list"
```

---

### update_shopping_list_label_settings — PUT /api/households/shopping/lists/{id}/label-settings

Sets the label display order on a shopping list to match a specific store's aisle layout.

```
"Set up my Kroger list so produce comes before dairy"
"Arrange my Aldi list labels in the order I walk the store"
"Update the label order on my shopping list for Costco"
```

> **Tip:** Use `get_labels` first to see your available label IDs, then specify the order.

---

### add_recipe_to_shopping_list — POST /api/households/shopping/lists/{id}/recipe/{recipe_id}

Adds all ingredients from a single recipe to an existing shopping list. Optionally scales quantities by a multiplier.

```
"Add the lasagna recipe ingredients to my shopping list"
"Add chicken soup ingredients to Weekly Groceries"
"Add the pasta recipe to my list with double quantities"
"Add lasagna for 8 people (recipe serves 4)"
```

---

### remove_recipe_from_shopping_list — POST /api/households/shopping/lists/{id}/recipe/{recipe_id}/delete

Removes the ingredients of a specific recipe from a shopping list.

```
"Remove the lasagna ingredients from my shopping list"
"Take the chicken soup items off my grocery list"
"I'm not making pasta anymore — remove it from the list"
```

---

### add_recipes_to_shopping_list_bulk — POST /api/households/shopping/lists/{id}/recipe

Adds multiple recipes' ingredients to a shopping list in a single operation. More efficient than adding recipes one at a time.

```
"Add all this week's dinner recipes to my shopping list at once"
"Add lasagna, chicken soup, and beef stew to my grocery list"
"Build a shopping list from Monday through Friday's meals"
```

---

### get_shopping_list_items — GET /api/households/shopping/items

Returns all shopping list items across all lists, with optional search and pagination.

```
"Show me all items on my shopping lists"
"Search for 'chicken' across my shopping items"
"Show me 50 items per page"
```

---

### get_shopping_list_item — GET /api/households/shopping/items/{id}

Returns a single shopping list item by ID.

```
"Get the details for the eggs item"
"Show me that specific shopping list item"
```

---

### create_shopping_list_item — POST /api/households/shopping/items

Adds a single item to a shopping list.

```
"Add eggs to my shopping list"
"Add 2 lbs of chicken breast to Weekly Groceries"
"Put milk on my grocery list"
```

---

### create_shopping_list_items_bulk — POST /api/households/shopping/items/create-bulk

Adds multiple items to a shopping list in a single operation.

```
"Add eggs, milk, and bread to my shopping list"
"Add these to my grocery list:
  - 2 lbs chicken breast
  - 1 dozen eggs
  - 2 cups rice
  - 1 lb butter"
```

---

### update_shopping_list_item — PUT /api/households/shopping/items/{id}

Updates a single shopping list item. Only the fields you specify are changed — all other fields are preserved automatically.

**Check off an item:**
```
"Mark eggs as checked on my shopping list"
"Check off milk from the grocery list"
"I bought the chicken breast — mark it as done"
```

**Update quantity or note:**
```
"Change the chicken breast to 3 lbs"
"Update the rice to 'Basmati rice, 2 cups'"
```

**Uncheck an item:**
```
"Uncheck the eggs on my shopping list"
"Mark milk as not yet purchased"
```

---

### update_shopping_list_items_bulk — PUT /api/households/shopping/items

Updates multiple shopping list items in a single operation.

```
"Check off eggs, milk, and bread on my shopping list"
"Mark all the produce items as checked"
"Update the quantities for chicken, rice, and pasta"
```

---

### delete_shopping_list_item — DELETE /api/households/shopping/items/{id}

Deletes a single item from a shopping list.

```
"Delete eggs from my shopping list"
"Remove the milk item from my grocery list"
"Take chicken breast off the list"
```

---

### delete_shopping_list_items_bulk — DELETE /api/households/shopping/items

Deletes multiple shopping list items in a single operation.

```
"Remove all checked items from my shopping list"
"Delete eggs, milk, and bread from my list"
"Clear all the checked items"
```

---

## Category Tools

Categories are read-only — you can browse and filter by them but not create or modify them through this server.

### get_categories — GET /api/organizers/categories

Returns all recipe categories with pagination.

```
"Show me all recipe categories"
"What categories do I have?"
"List my recipe categories"
```

---

### get_category — GET /api/organizers/categories/{id}

Returns a specific category and its associated recipes by ID.

```
"Show me the breakfast category"
"Get details for the dinner category"
```

---

### get_category_by_slug — GET /api/organizers/categories/slug/{slug}

Returns a category and its associated recipes by slug.

```
"Show me recipes in the 'breakfast' category"
"Get the 'side-dish' category"
"Find the 'dessert' category"
```

---

### get_empty_categories — GET /api/organizers/categories/empty

Returns categories that have no recipes assigned. Use this to find and clean up stale category entries after reorganizing your library.

```
"Show me any categories with no recipes"
"Which categories are empty?"
"Find unused categories I can clean up"
```

---

## Tag Tools

### get_empty_tags — GET /api/organizers/tags/empty

Returns tags that have no recipes assigned. Use this to clean up orphaned tags after reorganizing.

```
"Show me any tags with no recipes"
"Which tags are unused?"
"Find empty tags I can clean up"
```

---

### get_tags — GET /api/organizers/tags

Returns all recipe tags with pagination.

```
"Show me all tags"
"What tags do I have?"
"List all my recipe tags"
```

---

### get_tag — GET /api/organizers/tags/{id}

Returns a specific tag and its associated recipes by ID.

```
"Show me the healthy tag"
"Get details for the quick tag"
```

---

### get_tag_by_slug — GET /api/organizers/tags/slug/{slug}

Returns a tag and its associated recipes by slug.

```
"Show me recipes tagged 'quick-meals'"
"Get the 'vegetarian' tag"
"Find recipes with the 'high-protein' tag"
```

---

## Food Tools

### get_foods — GET /api/foods

Returns all ingredient foods with optional search and pagination.

```
"Show me all foods in the database"
"Search for 'chicken' in the foods list"
"Find foods matching 'rice'"
```

---

### get_food — GET /api/foods/{id}

Returns a specific food item by ID, including label and alias information.

```
"Get details for that food item"
"Show me the food entry for chicken breast"
```

---

### create_food — POST /api/foods

Adds a new food to the ingredient library. Always search with `get_foods` first — only create if no match exists. Assign a shopping list label so the food appears in the right aisle.

```
"Add 'coconut aminos' to the food library under Condiments"
"Create a food entry for 'cassava flour' in the Baking section"
"Add 'fresh turmeric' to the food library"
```

> **Tip:** The `recipe_builder` prompt handles food creation automatically during recipe building. Use `create_food` directly only when adding a standalone food entry.

---

### merge_foods — PUT /api/foods/merge

Merges a duplicate food into a canonical entry. All recipe references to the source food are updated to the target, then the source is deleted. Use `get_foods` to find both UUIDs first.

```
"Merge 'chicken breasts' into 'chicken breast'"
"Consolidate 'roma tomatoes' and 'roma tomato' into one entry"
"Merge the duplicate garlic entries"
```

---

## Meal Plan Tools

### get_all_mealplans — GET /api/households/mealplans

Returns all meal plan entries with optional date filtering and pagination.

```
"Show me all my meal plans"
"What meals do I have planned?"
"Show me meal plans from Monday to Friday"
"Get meal plans for next week"
"What did I have planned last Wednesday?"
```

---

### get_todays_mealplan — GET /api/households/mealplans/today

Returns all meal plan entries for today.

```
"What's on the meal plan for today?"
"What am I having for dinner tonight?"
"Show me today's meals"
"What's for breakfast today?"
```

---

### create_mealplan — POST /api/households/mealplans

Creates a single meal plan entry for a specific date.

```
"Add lasagna to Thursday's dinner"
"Plan chicken soup for lunch on Friday"
"Add the pasta recipe to tomorrow's dinner"
"Set oatmeal as Monday's breakfast"
```

---

### create_mealplan_bulk — POST /api/households/mealplans (loop)

Creates multiple meal plan entries at once.

```
"Plan this week's dinners:
  - Monday: Lasagna
  - Tuesday: Chicken stir-fry
  - Wednesday: Spaghetti
  - Thursday: Tacos
  - Friday: Pizza"

"Add breakfast and dinner for the next 3 days"
"Plan all my meals for next week"
```

---

### update_mealplan — PUT /api/households/mealplans/{id}

Updates an existing meal plan entry — change the date, meal type, or recipe assignment.

```
"Move Thursday's lasagna to Friday"
"Change Wednesday's lunch to chicken soup"
"Swap Saturday's breakfast to pancakes"
"Move tonight's dinner to tomorrow"
```

---

### delete_mealplan — DELETE /api/households/mealplans/{id}

Removes an entry from the meal plan.

```
"Remove Thursday's lunch from the meal plan"
"Delete Saturday's breakfast"
"Clear Sunday's dinner — we're eating out"
```

---

## Cookbook Tools

### get_cookbooks — GET /api/households/cookbooks

Returns all cookbooks (curated recipe collections) in the household.

```
"Show me all my cookbooks"
"What cookbooks do I have?"
"List my recipe collections"
```

---

## Organizer Tools

### get_cooking_tools — GET /api/organizers/tools

Lists all cooking tools used to tag recipes by required equipment.

```
"What cooking tools do I have set up?"
"Show me all equipment tags"
"List tools like stand mixer, instant pot, grill"
```

> **Tip:** Use this to find tool slugs before filtering recipes by required equipment with `get_recipes`.

---

### get_units — GET /api/organizers/units

Lists all units of measurement used in recipe ingredient quantities.

```
"Show me all units of measurement"
"What units do I have — cups, grams, tablespoons?"
"List all ingredient units"
```

---

### get_labels — GET /api/organizers/labels

Lists all shopping list labels used to categorize and sort items by store section.

```
"Show me all shopping list labels"
"What grocery sections do I have set up?"
"List my store section labels"
```

> **Tip:** Use this with `update_shopping_list_label_settings` to set the aisle order for a specific store.

---

## Workflows

### Full cooking flow — from plan to notes

```
1. "What am I making tonight?"          → get_todays_mealplan
2. "Get me ready to cook the lasagna"   → cooking_session prompt
3. "Do I have all the equipment?"       → assistant checks tools against get_cooking_tools
4. [After cooking] "Add a note: used half the ricotta, still great"  → create_recipe_comment
5. "Mark it as made"                    → mark_recipe_last_made
```

---

### Weekly planning with shopping trip

```
1. Use weekly_meal_plan prompt → assistant plans 7 days, asks for swaps, saves to Mealie
2. Use shopping_trip prompt    → assistant builds labeled shopping list with cost estimate
3. [At the store] "Check off eggs, milk, and chicken"  → update_shopping_list_items_bulk
4. "Remove all checked items"  → delete_shopping_list_items_bulk
```

---

### Share a recipe with family

```
1. "Create a share link for the lasagna recipe"  → create_recipe_share_token
2. "Get the PDF download link too"               → get_recipe_exports
   → text both links to mom
```

---

### Store-specific shopping list setup

```
1. "Show me my shopping list labels"    → get_labels (note the IDs)
2. "Create a new list called 'Kroger'" → create_shopping_list
3. "Set up the label order for Kroger — produce first, then dairy, then meat"
                                        → update_shopping_list_label_settings
4. "Add this week's meals to the Kroger list"
                                        → add_recipes_to_shopping_list_bulk
```

---

### Nutrition check

```
1. Use nutrition_summary prompt for "this week"
   → assistant fetches each meal plan recipe, sums macros
   → flags any recipes missing nutrition data
2. "Which of my recipes are missing nutrition info?" → assistant lists them from above
```

---

### Recipe history and review

```
1. "What did I eat last week?"          → weekly_review prompt (period="last week")
2. "When did I last make beef stew?"   → get_recipe_timeline (search results)
3. "What notes did I leave on it?"     → get_recipe_comments
4. "Plan it again for this Thursday"   → create_mealplan
```

---

### Dinner party prep

```
1. "Add lasagna for 8 (recipe serves 4) to my shopping list with 2x quantities"
                                        → add_recipe_to_shopping_list (recipeIncrementQuantity=2)
2. "Also add a bottle of wine and some bread" → create_shopping_list_items_bulk
3. "Show me the full list"              → get_shopping_list
4. "Create a share link so guests can see the recipe" → create_recipe_share_token
```

---

## Tips

### Use slugs for filtering

Always get slugs first before filtering — display names won't work.

```
Step 1: "Show me all tags"
Step 2: Note the slug (e.g. "quick-meals")
Step 3: "Find recipes tagged 'quick-meals'"
```

### Use concise for planning, detailed for cooking

```
Meal planning → get_recipe_concise   (fast, low token usage)
Cooking       → get_recipe_detailed  (full ingredients, instructions, nutrition)
```

### Batch operations save round trips

```
✅ "Add eggs, milk, and bread to my shopping list"   [one bulk call]
❌ "Add eggs" / "Add milk" / "Add bread"             [three separate calls]
```

### Field preservation on updates

When updating a shopping list item, only fields you mention are changed. Everything else stays as-is.

```
"Mark eggs as checked"
→ Only the checked field changes. Note, quantity, unit, etc. are untouched.
```

### Scale recipe quantities

```
"Add the lasagna recipe with 2x quantities"   → recipe serves 4, now serves 8
"Add chicken soup for 6 (recipe serves 2)"   → recipeIncrementQuantity=3
```
