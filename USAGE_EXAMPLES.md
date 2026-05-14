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
- [Workflows](#workflows)

---

## Server Prompts

MCP prompts are pre-built conversation starters that inject system instructions and context into the AI assistant before the conversation begins. Unlike regular chat messages, prompts configure how the assistant approaches a task — what tools to use, in what order, and how to present results.

### weekly_meal_plan

**What it does:** Starts a guided meal planning session. The assistant is pre-instructed to search your Mealie recipe database, present a full 7-day plan (breakfast, lunch, dinner) in table format, ask for feedback, and save the confirmed plan to Mealie.

**How to invoke in Claude:**
1. Open a new conversation
2. Click the **Attach** or **+** button and select **Mealie MCP Server**
3. Choose **weekly_meal_plan** from the prompt list
4. Optionally fill in the `preferences` field before submitting

**How to invoke in ChatGPT:**
1. Open a new conversation with the Mealie connector active
2. Type `/weekly_meal_plan` or select it from the prompt menu

**The `preferences` parameter (optional):**

If left empty, the assistant plans a balanced general week. If provided, your preferences are appended to the opening user message and the assistant tailors the plan accordingly.

```
preferences: "vegetarian, no nuts, prefer quick weeknight meals"
preferences: "high protein, Mediterranean style"
preferences: "family of 4, budget-friendly, kid-friendly meals"
```

**What happens behind the scenes:**
1. The assistant receives system instructions covering which tools to use (`get_recipes`, `get_recipe_concise`, `create_mealplan_bulk`) and how to interact with you
2. The conversation opens with: *"I need help creating a balanced meal plan for the next week..."* (plus your preferences if provided)
3. The assistant searches your recipe database, proposes a plan, asks for swaps or adjustments, then saves the final plan to Mealie on your confirmation

---

## Recipe Tools

### get_recipes — GET /api/recipes

Lists and searches recipes with optional filtering.

```
"Show me all my recipes"
"Search for chicken recipes"
"Find recipes with 'pasta' in the name"
"Show me 20 recipes per page"
```

**Filtering by category (use slugs, not display names):**
```
"Get all breakfast recipes"
"Find recipes in the dinner category"
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

Returns the full recipe including all ingredients, step-by-step instructions, nutrition info, notes, and metadata.

```
"Show me the full lasagna recipe"
"Get all the details for chicken parmesan"
"Show me the complete instructions for beef stew"
```

---

### get_recipe_concise — GET /api/recipes/{slug}

Returns a summary of a recipe — name, servings, total time, rating, ingredients list, and last made date. Used by default when full details aren't needed (e.g. during meal planning).

```
"Give me a quick summary of the lasagna recipe"
"What are the ingredients and servings for chicken soup?"
"How long does the pasta recipe take?"
```

---

### mark_recipe_last_made — PATCH /api/recipes/{slug}/last-made

Updates the last made timestamp on a recipe to today's date.

```
"Mark the chicken parmesan as made today"
"Update the last made date for lasagna"
"I just made the beef stew — mark it as made"
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
"Start a new shopping list for meal prep"
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

### delete_shopping_list — DELETE /api/households/shopping/lists/{id}

Permanently deletes a shopping list and all its items.

```
"Delete my old shopping list"
"Remove the Thanksgiving list"
"Get rid of my Weekly Groceries list"
```

---

### add_recipe_to_shopping_list — POST /api/households/shopping/lists/{id}/recipe/{recipe_id}

Adds all ingredients from a recipe to an existing shopping list. Optionally scales quantities by a multiplier.

```
"Add the lasagna recipe ingredients to my shopping list"
"Add chicken soup ingredients to Weekly Groceries"
"Add the pasta recipe to my list with double quantities"
"Add lasagna ingredients for 8 people (recipe serves 4)"
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

### get_empty_categories — GET /api/organizers/categories/empty

Returns categories that have no recipes assigned to them.

```
"Which categories have no recipes?"
"Show me empty categories"
"Find unused categories"
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
"Get the 'quick-meals' category"
"Find the 'desserts' category"
```

---

## Tag Tools

Tags are read-only — you can browse and filter by them but not create or modify them through this server.

### get_tags — GET /api/organizers/tags

Returns all recipe tags with pagination.

```
"Show me all tags"
"What tags do I have?"
"List all my recipe tags"
```

---

### get_empty_tags — GET /api/organizers/tags/empty

Returns tags that have no recipes assigned to them.

```
"Which tags have no recipes?"
"Show me unused tags"
"Find empty tags"
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

Foods are read-only — you can browse the ingredient food database but not modify it through this server.

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

## Meal Plan Tools

### get_all_mealplans — GET /api/households/mealplans

Returns all meal plan entries with optional date filtering and pagination.

```
"Show me all my meal plans"
"What meals do I have planned?"
"Show me meal plans from Monday to Friday"
"Get meal plans for next week"
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

Creates a single meal plan entry for a specific date. Supports breakfast, lunch, dinner, and side entry types.

```
"Add lasagna to Thursday's dinner"
"Plan chicken soup for lunch on Friday"
"Add the pasta recipe to tomorrow's dinner"
"Set oatmeal as Monday's breakfast"
```

---

### create_mealplan_bulk — POST /api/households/mealplans (loop)

Creates multiple meal plan entries at once by looping through a list of entries.

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

## Workflows

### From recipe to table

A complete end-to-end flow for a single meal:

```
1. "Find a chicken recipe for tonight"
2. "Add it to today's dinner plan"
3. "Add the ingredients to my shopping list"
4. [After cooking] "Mark it as made"
```

### Weekly meal planning with shopping

```
1. "Help me plan this week's dinners" [assistant searches recipes, proposes plan]
2. "Swap Wednesday's meal for something vegetarian"
3. "That looks good — save it"
4. "Now create a shopping list from this week's meal plan"
5. [At the store] "Check off eggs, milk, and chicken"
6. "Remove all checked items from the list"
```

### Recipe discovery and organization

```
"Show me all my tags"
[Note the slug for 'quick-meals']
"Find recipes tagged 'quick-meals' in the dinner category"
"Show me the ones I haven't made recently"
"Add the top 3 to next week's meal plan"
```

### Dinner party shopping

```
"I'm making lasagna for 8 (recipe serves 4) — add the ingredients with double quantities to my shopping list"
"Also add a bottle of wine and some bread"
"Show me the full list"
```

### Post-shopping cleanup

```
"Check off everything I bought"
"Remove all checked items from my grocery list"
```

### Weekly prompt-driven planning

Use the built-in `weekly_meal_plan` prompt for a guided experience:

```
preferences: "quick weeknight meals, family of 4, avoid fish"
```

The assistant will search your Mealie database, propose a full 7-day plan, ask for any swaps, and save the confirmed plan — all in one conversation.

---

## Tips

### Use slugs for filtering

Always get slugs first before filtering — display names won't match.

```
Step 1: "Show me all tags"
Step 2: Note the slug (e.g. "quick-meals")
Step 3: "Find recipes tagged 'quick-meals'"
```

### Batch operations save round trips

```
✅ "Add eggs, milk, and bread to my shopping list" [one bulk call]
❌ "Add eggs" / "Add milk" / "Add bread" [three separate calls]
```

### Field preservation on updates

When updating a shopping list item, only fields you mention are changed. Everything else stays as-is.

```
"Mark eggs as checked"
→ Only the checked field changes. Note, quantity, unit, etc. are untouched.
```

### Scale recipe quantities when adding to shopping lists

```
"Add the lasagna recipe with 2x quantities" [serves 4 → serves 8]
```
