# LLM Integration Test Prompt

Paste this into Claude or ChatGPT with the Mealie MCP server connected.
All tools are read-only. If a tool fails, paste the full error and JSON back for diagnosis.

---

Using the Mealie MCP server, call every read-only tool listed below exactly once.
Call them in a logical order — use results from earlier calls to get IDs and slugs
needed for later calls. For tools that require an ID (get_category, get_tag, get_food,
get_shopping_list, get_shopping_list_item), use the first ID returned by the
corresponding list call. If a list is empty, skip tools that require an item from it.

For each tool call:
- If it succeeds: say PASS and the tool name
- If it fails: say FAIL, the tool name, the full error message, and the raw JSON response

Tools to call:
- get_shopping_lists
- get_tags
- get_tag
- get_tag_by_slug
- get_recipes
- get_recipe_detailed
- get_recipe_concise
- get_recipe_comments
- get_recipe_timeline
- get_recipe_share_tokens
- get_categories
- get_category
- get_category_by_slug
- get_empty_categories
- get_empty_tags
- get_foods
- get_food
- get_shopping_list
- get_shopping_list_items
- get_shopping_list_item
- get_all_mealplans
- get_todays_mealplan
- get_cookbooks
- get_cooking_tools
- get_units
- get_labels

At the end, print a summary: X/Y passed, and list any failures.

---

## ChatGPT note

ChatGPT's safety filter may block certain tool calls with "This tool call was blocked by OpenAI's safety checks."
This is a false positive — the tools are read-only and the requests never reach the server. Known false-positive
tools: `get_tag`, `get_tag_by_slug`, `get_shopping_lists`, `get_recipe_comments`, `get_category`, `get_food`,
`get_shopping_list_item`, `get_cookbooks`. The filter is more likely to trigger after a large amount of
conversation context has accumulated. If a block occurs, note it as a platform issue, not a server error.
