from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.prompts.base import AssistantMessage, Message, UserMessage


def register_prompts(mcp: FastMCP) -> None:
    """Register all prompt-related tools with the MCP server."""

    @mcp.prompt()
    def weekly_meal_plan(
        days: int = 7,
        tags: str = "",
        meals: str = "Breakfast,Lunch,Dinner,Side Dish,Snack,Dessert",
        notes: str = "",
    ) -> list[Message]:
        """Generates a weekly meal plan from your Mealie recipe library.

        Args:
            days: Number of days to plan (default 7)
            tags: Comma-separated list of tags to filter recipes (empty = all recipes)
            meals: Comma-separated meal categories to include per day
            notes: Additional strict dietary notes or constraints
        """
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        meal_list = [m.strip() for m in meals.split(",") if m.strip()]

        tag_instructions = (
            f"Only include recipes matching ALL of these tags: {tag_list}"
            if tag_list
            else "Allow all recipes regardless of tags."
        )

        notes_instructions = (
            f"Follow these notes STRICTLY. Do not infer additional restrictions beyond what is written: {notes}"
            if notes
            else "No additional notes."
        )

        system_content = f"""
<context>
You have access to a Mealie recipe database. Connect to the MCP server and pull all available recipes before planning.

## Tool Usage
- get_recipes: always set per_page=50; use null for empty values
- get_recipe_concise: use by default for recipe details
- get_recipe_detailed: only if the user explicitly asks for full details
- get_all_mealplans: check existing plans before creating new ones
- create_mealplan_bulk: save the approved plan (requires date YYYY-MM-DD, recipe_id, entry_type)
- get_tags: use to resolve tag slugs before filtering
- get_categories: use to resolve category slugs before filtering
</context>

<instructions>
## Variables
- Days: {days}
- Tag filter: {tag_instructions}
- Meal categories per day: {meal_list}
- Notes: {notes_instructions}

## Tag Filtering
- Category slugs must be used when filtering (e.g. "side-dish", not "Side Dish")
- Use get_tags and get_categories to resolve slugs before filtering

## Meal Assignment Rules
- Use the provided meal categories
- Categories map directly to recipe categories in Mealie
- Each day must include all requested meal categories

## Uniqueness & Leftovers
- Prefer unique recipes whenever possible
- If recipe count is limited, recipe reuse is allowed
- Each cooked recipe may be used for up to 2 meals total
- Dinner leftovers may be reused for Lunch
- Do NOT overuse leftovers or make every lunch leftovers

## Recipe Usage Rules
- Prefer existing recipes over generic or invented foods
- Only create simple non-recipe foods when required
- Do NOT replace an available recipe with a generic equivalent

## Sandwich Rules
- "Sandwich" recipes are sandwich fillings
- "Sandwich Bread" recipes are required for sandwiches
- A sandwich must include at least 1 Sandwich recipe and at least 1 Sandwich Bread recipe
- Prefer Sandwich Bread recipes over generic bread
- Multiple Sandwich fillings are allowed
- You may add simple ingredients: eggs, cheese, bacon, lettuce, tomato
- Do NOT place unrelated recipes inside sandwiches

## Missing Meal Handling
- If no valid recipe exists for a required category:
  - create a simple realistic food using basic ingredients
  - keep it minimal
  - prefer foods already in the Mealie food database

## User Interaction
- Present the meal plan in table format
- Ask for feedback about meal swaps, leftover utilization, and dietary needs
- Before saving to Mealie, display the complete meal plan in concise summary for final user confirmation
- After confirmation, save the plan to Mealie without showing an additional summary

## Output Format
Day 1
  Breakfast:
  Lunch:
  Dinner:
  Side Dish:
  Snack:
  Dessert:

Day 2
  ...
</instructions>
"""

        user_content = f"Please create a {days}-day meal plan using my Mealie recipes."
        if notes:
            user_content += f" Notes: {notes}"

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]

    @mcp.prompt()
    def shopping_trip(
        store: str = "",
        notes: str = "",
    ) -> list[Message]:
        """Builds a consolidated shopping list from the current meal plan,
        grouped by grocery store section, with cost estimation.

        Args:
            store: Store name for label ordering (e.g. "Kroger", "Aldi")
            notes: Additional notes or exclusions
        """
        store_note = f"Optimize label order for {store}." if store else "Use default label order."

        system_content = f"""
<context>
You have access to a Mealie MCP server. Use the following tools to build a shopping list:
- get_all_mealplans: fetch the current week's meal plan
- get_recipe_detailed: fetch full ingredient lists for each recipe
- get_labels: fetch available shopping list labels (grocery store sections)
- get_shopping_lists: check for an existing shopping list to update
- create_shopping_list: create a new shopping list if needed
- add_recipes_to_shopping_list_bulk: add all meal plan recipes at once
- update_shopping_list_label_settings: set label order for the target store
</context>

<instructions>
## Store
{store_note}

## Shopping List Generation
1. Fetch this week's meal plan
2. Collect all recipes from the plan
3. Add all recipes to the shopping list in one bulk operation
4. Consolidate duplicate ingredients into total quantities
5. Group items by food label / grocery store section

## Grocery Store Sections
Use these labels in order when grouping:
- Baked Goods
- Baking
- Beverages
- Canned & Jarred Goods
- Cereals
- Cheese
- Condiments
- Dairy & Eggs
- Dairy-Free
- Dressings & Vinegars
- Frozen Foods
- Fruits
- Herbs & Spices
- Legumes
- Meats
- Mushrooms
- Nuts & Seeds
- Oils & Fats
- Packaged & Prepared Foods
- Pasta
- Poultry
- Pre-Made Doughs & Wrappers
- Rice and Grains
- Sauces, Spreads & Dips
- Seafood
- Seasonings & Spice Blends
- Snacks
- Soups, Stews & Stock
- Sugar & Sweeteners
- Supplements & Extracts
- Vegetables & Greens
- Wine, Beer & Spirits

## Grocery Cost Estimation
- Exclude pantry staples from cost estimate
- Prefer simple, affordable, and organic foods when realistic

## Notes
{notes if notes else "None."}

## Output Format
Shopping List
  Vegetables & Greens:
    - item
  Dairy & Eggs:
    - item

Estimated Cost:
  - Approximate Total:
  - Notes:
</instructions>
"""

        user_content = "Build a shopping list from my current meal plan."
        if store:
            user_content += f" I'm shopping at {store}."
        if notes:
            user_content += f" Notes: {notes}"

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]

    @mcp.prompt()
    def cooking_session(recipe: str = "") -> list[Message]:
        """Prepares everything you need before starting to cook — recipe details,
        required equipment, units, and existing cooking notes.

        Args:
            recipe: Recipe name or slug to cook (leave empty to use today's meal plan)
        """
        system_content = """
<context>
You have access to a Mealie MCP server. Use the following tools:
- get_todays_mealplan: fetch today's planned meals if no recipe is specified
- get_recipe_detailed: fetch full recipe with ingredients, instructions, nutrition, and notes
- get_recipe_comments: fetch existing cooking notes for the recipe
- get_cooking_tools: fetch available cooking tools to match against recipe requirements
- get_units: fetch units of measurement if clarification is needed
</context>

<instructions>
## Setup
1. If a recipe was specified, fetch it directly by slug or name
2. If no recipe was specified, fetch today's meal plan and ask which meal to cook
3. Fetch full recipe details including ingredients, instructions, and nutrition
4. Fetch any existing comments/cooking notes on the recipe
5. Match recipe tool requirements against available cooking tools

## Output Format
Present the following in a clean, easy-to-read format:

**Recipe:** [name]
**Servings:** [servings]
**Total Time:** [time]

**Required Equipment:**
- [tool list]

**Ingredients:**
- [grouped by use if possible]

**Instructions:**
1. [steps]

**Previous Cooking Notes:**
- [comments if any]

**Nutrition (per serving):**
- [macros if available]
</instructions>
"""

        user_content = (
            f"I'm about to cook {recipe}. Get me everything I need."
            if recipe
            else "What am I cooking today? Get me everything I need to start."
        )

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]

    @mcp.prompt()
    def weekly_review(period: str = "this week") -> list[Message]:
        """Reviews your cooking and eating history — what you made, when you made it,
        and patterns over time.

        Args:
            period: Time period to review (e.g. "this week", "last week", "last 30 days")
        """
        system_content = f"""
<context>
You have access to a Mealie MCP server. Use the following tools:
- get_all_mealplans: fetch meal plan history for the requested period
- get_recipe_timeline: fetch a chronological activity feed of recipe events
- get_recipe_concise: fetch recipe summaries as needed
- get_recipe_comments: fetch cooking notes for specific recipes if the user asks
</context>

<instructions>
## Period
Review period: {period}

## Review Steps
1. Fetch meal plan history for the period
2. Fetch the recipe timeline to capture cooking activity
3. Summarize what was eaten each day
4. Identify any patterns (repeated meals, unused categories, heavy protein days, etc.)
5. Note the last time each recipe appeared

## Answer Common Questions
- "What did I eat last Wednesday?"
- "What have I been cooking lately?"
- "When did I last make [recipe]?"
- "What proteins have I been eating most?"

## Output Format
**Meal Plan Summary ({period}):**
[Day-by-day breakdown]

**Patterns Noticed:**
- [observations]

**Recipe Activity:**
- [recent timeline events]
</instructions>
"""

        user_content = f"Review my cooking and eating history for {period}."

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]

    @mcp.prompt()
    def recipe_builder(
        name: str = "",
        source: str = "",
        cookbook: str = "my-recipes",
    ) -> list[Message]:
        """Guides the creation of a new recipe in Mealie using your existing
        category, tag, tool, and food conventions.

        Args:
            name: Recipe name if already known (leave empty to discuss first)
            source: Where the recipe comes from (website, cookbook, memory, etc.)
            cookbook: Which cookbook to assign — "my-recipes" (default) or "the-autoimmune-solution"
        """
        source_note = f"Source: {source}" if source else "Source: not specified."
        name_note = f'Recipe name: "{name}"' if name else "Recipe name: to be determined."

        system_content = f"""
<context>
You have access to a Mealie MCP server. Use the following tools to build and save a recipe:
- get_recipes: fetch existing recipes to observe naming and tagging patterns
- get_recipe_detailed: fetch 2-3 similar recipes to use as a template for categories/tags/tools
- get_categories: fetch all available category slugs
- get_tags: fetch all available tag slugs
- get_cooking_tools: fetch all available tool slugs
- get_foods: search the food library before adding any ingredient
- get_labels: fetch available shopping list labels to assign to new foods
- create_food: add a new food only if it does not exist in the library
- create_recipe: create the recipe once all fields are confirmed
</context>

<instructions>
## Setup
{name_note}
{source_note}
Cookbook tag to assign: {cookbook}

## Step 1 — Learn the conventions
Before asking the user for any details, fetch 2-3 existing recipes that are similar in type
(e.g., if this is a chicken dinner, fetch other chicken dinner recipes). Use get_recipe_detailed.
Observe which categories, tags, and tools appear on those recipes — follow those patterns exactly.
Do not invent new category/tag/tool combinations that aren't already in use.

## Step 2 — Gather recipe details
Ask the user for all required details conversationally. Collect:
- Name (if not provided)
- Description (1-2 sentences)
- Categories (match existing patterns)
- Tags (match existing patterns; always include "{cookbook}")
- Required cooking tools (match existing patterns)
- Ingredients — for each: quantity, unit, food name, and any note
- Instructions — numbered steps; use section headers if needed
- Prep time, cook time, total time — plain text (e.g. "30 minutes", "1 hour", "1 hour 30 minutes")
- Servings and yield — three independent fields:
    - recipeServings: number of people served (e.g. 2)
    - recipeYieldQuantity: total output quantity (e.g. 6 for 6 fillets, 2 for 2 cups)
    - recipeYield: unit + per-serving breakdown (e.g. "fillets (3 fillets per serving)", "cups (1/2 cup per serving)")
  Nutrition values are per serving.
- Source URL if applicable
- Nutrition — required; estimate from standard sources if the user doesn't have exact values.
  All eleven fields must be populated: calories, carbohydrate, cholesterol, fat, fiber, protein,
  saturated fat, sodium, sugar, trans fat, unsaturated fat. Values are strings (e.g. "250").
- Notes (optional tips, variations, storage instructions)

## Step 3 — Resolve ingredients
For each ingredient, search get_foods by name before using it.
- If an exact or very close match exists, use that food name exactly as it appears in the library.
- If no match exists, use the new food name as-is — create_recipe will auto-create it.
  However, if you want the food to have a shopping list label (aisle), create it manually first:
  1. Call get_labels to find the appropriate label (e.g. "Vegetables & Greens", "Meats", "Dairy & Eggs")
  2. Call create_food with the food name and the matching label_id
- Do not silently invent food names that differ from what's in the library.

## Step 4 — Present preview
Display the complete recipe in recipe-card format for user confirmation:

**[Recipe Name]**
*[Description]*

Categories: | Tags: | Tools:
Servings: | Prep: | Cook: | Total:

**Ingredients:**
[grouped by section if applicable]

**Instructions:**
[numbered steps]

**Notes:** (if any)

Ask: "Does this look correct? Any changes before I save it?"

## Step 5 — Save
On confirmation:
1. Call create_recipe with the fully structured RecipeCreate payload.
2. Confirm success and show the recipe slug for reference.
3. Do not show an additional summary after saving — the preview was the summary.
</instructions>
"""

        user_content = (
            f'I want to add "{name}" to my recipe library.'
            if name
            else "I want to add a new recipe to my library."
        )
        if source:
            user_content += f" It's from {source}."

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]

    @mcp.prompt()
    def nutrition_summary(period: str = "today") -> list[Message]:
        """Calculates caloric and macro intake from your meal plan.

        Args:
            period: Time period to calculate (e.g. "today", "this week")
        """
        system_content = f"""
<context>
You have access to a Mealie MCP server. Use the following tools:
- get_todays_mealplan: if period is "today"
- get_all_mealplans: if period spans multiple days
- get_recipe_detailed: fetch full recipe details including nutrition data per recipe
</context>

<instructions>
## Period
Calculate nutrition for: {period}

## Calculation Steps
1. Fetch the meal plan for the requested period
2. For each recipe in the plan, fetch full recipe details to get nutrition data
3. Sum macros across all meals: calories, carbohydrates, fat, protein, fiber, sodium, sugar
4. Divide by servings as appropriate
5. Flag any recipes that are missing nutrition data — do not silently skip them

## Missing Data Handling
- If a recipe has no nutrition data, note it explicitly
- Offer to estimate based on ingredients if the user wants
- Do not silently return zeros for missing data

## Output Format
**Nutrition Summary ({period}):**

| Meal | Recipe | Calories | Carbs | Fat | Protein |
|------|--------|----------|-------|-----|---------|
| ...  | ...    | ...      | ...   | ... | ...     |

**Daily Totals:**
- Calories:
- Carbohydrates:
- Fat:
- Protein:
- Fiber:
- Sodium:
- Sugar:

**Missing Nutrition Data:**
- [list any recipes without data]
</instructions>
"""

        user_content = f"Calculate my caloric and macro intake for {period}."

        return [
            AssistantMessage(system_content),
            UserMessage(user_content),
        ]
