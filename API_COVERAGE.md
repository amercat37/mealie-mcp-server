# API Coverage Report

This document compares the MCP server implementation against the official Mealie API.

## Summary

| Category | Total Endpoints | Implemented | Coverage |
|----------|----------------|-------------|----------|
| Recipe Operations | 20 | 4 | 20% |
| Shopping Lists | 17 | 13 | 76% |
| Categories | 7 | 4 | 57% |
| Tags | 7 | 4 | 57% |
| Meal Plans | 7 | 4 | 57% |
| Foods | 7 | 2 | 29% |
| Recipe Advanced Features | — | 0 | — |
| Household Management | — | 0 | — |
| Organizer Extras | — | 0 | — |
| Admin & User Management | — | 0 | — |
| **Total Priority APIs** | **65** | **31** | **48%** |

## Detailed Coverage

### ✅ Recipe Operations (4/20 implemented)

**Implemented:**
- ✅ `GET /api/recipes` - Search and filter the recipe library with pagination and advanced filtering
- ✅ `GET /api/recipes/{slug}` - Fetch full recipe details including ingredients, instructions, and nutrition
- ✅ `GET /api/recipes/{slug}` - Fetch a concise recipe summary (name, tags, categories, image only)
- ✅ `PATCH /api/recipes/{slug}/last-made` - Record today's date as the last time this recipe was made

**Not Implemented:**
- 🚫 `POST /api/recipes` - Create a new recipe from scratch
- 🚫 `PUT /api/recipes/{slug}` - Replace all fields of an existing recipe with a new version
- 🚫 `PATCH /api/recipes/{slug}` - Update individual recipe fields without replacing the whole record
- 🚫 `DELETE /api/recipes/{slug}` - Permanently delete a recipe
- 🚫 `POST /api/recipes/{slug}/duplicate` - Clone a recipe under a new name
- 🚫 `POST /api/recipes/{slug}/image` - Scrape and attach an image to a recipe from a URL
- 🚫 `PUT /api/recipes/{slug}/image` - Upload an image file directly to a recipe
- 🚫 `POST /api/recipes/{slug}/assets` - Attach a file asset (PDF, etc.) to a recipe
- 🚫 `POST /api/recipes/create/url` - Scrape a recipe from a web URL and import it into Mealie
- 🚫 `POST /api/recipes/create/url/bulk` - Import multiple recipes from a list of URLs in one request
- 🚫 `POST /api/recipes/create/zip` - Import recipes from a Mealie-formatted ZIP archive
- 🚫 `POST /api/recipes/create/html-or-json` - Import a recipe from raw HTML or JSON-LD markup
- 🚫 `PUT /api/recipes` - Apply full field replacement to multiple recipes in one request
- 🚫 `PATCH /api/recipes` - Apply partial field updates to multiple recipes in one request

### ✅ Shopping Lists (13/17 implemented)

**Shopping List Management:**
- ✅ `GET /api/households/shopping/lists` - List all shopping lists for the household
- ✅ `POST /api/households/shopping/lists` - Create a new empty shopping list
- ✅ `GET /api/households/shopping/lists/{id}` - Fetch a shopping list and its metadata by ID
- ✅ `DELETE /api/households/shopping/lists/{id}` - Delete a shopping list and all its items

**Recipe Integration:**
- ✅ `POST /api/households/shopping/lists/{id}/recipe/{recipe_id}` - Add all ingredients from a recipe to a shopping list
- ✅ `POST /api/households/shopping/lists/{id}/recipe/{recipe_id}/delete` - Remove a recipe's ingredients from a shopping list

**Shopping List Items:**
- ✅ `GET /api/households/shopping/items` - List all items across shopping lists, filterable by list
- ✅ `GET /api/households/shopping/items/{id}` - Fetch a single shopping list item by ID
- ✅ `POST /api/households/shopping/items` - Add a single item to a shopping list
- ✅ `POST /api/households/shopping/items/create-bulk` - Add multiple items to a shopping list in one request
- ✅ `PUT /api/households/shopping/items/{id}` - Update a shopping list item (text, checked state, quantity, etc.)
- ✅ `PUT /api/households/shopping/items` - Update multiple shopping list items in one request
- ✅ `DELETE /api/households/shopping/items/{id}` - Remove a single item from a shopping list
- ✅ `DELETE /api/households/shopping/items` - Remove multiple items from a shopping list by query parameters

**Not Implemented:**
- 🚫 `PUT /api/households/shopping/lists/{id}` - Rename or update the metadata of an existing shopping list
- 🚫 `PUT /api/households/shopping/lists/{id}/label-settings` - Configure which labels appear and in what order on a shopping list
- 🚫 `POST /api/households/shopping/lists/{id}/recipe` - Add multiple recipes' ingredients to a shopping list in one request

### ✅ Categories (4/7 implemented)

**Implemented:**
- ✅ `GET /api/organizers/categories` - List all recipe categories
- ✅ `GET /api/organizers/categories/empty` - List categories that have no recipes assigned
- ✅ `GET /api/organizers/categories/{id}` - Fetch a single category and its assigned recipes by ID
- ✅ `GET /api/organizers/categories/slug/{slug}` - Fetch a category by its URL-friendly slug

**Not Implemented:**
- 🚫 `POST /api/organizers/categories` - Create a new recipe category
- 🚫 `PUT /api/organizers/categories/{id}` - Rename or update a category
- 🚫 `DELETE /api/organizers/categories/{id}` - Delete a category

### ✅ Tags (4/7 implemented)

**Implemented:**
- ✅ `GET /api/organizers/tags` - List all recipe tags
- ✅ `GET /api/organizers/tags/empty` - List tags that have no recipes assigned
- ✅ `GET /api/organizers/tags/{id}` - Fetch a single tag and its assigned recipes by ID
- ✅ `GET /api/organizers/tags/slug/{slug}` - Fetch a tag by its URL-friendly slug

**Not Implemented:**
- 🚫 `POST /api/organizers/tags` - Create a new recipe tag
- 🚫 `PUT /api/organizers/tags/{id}` - Rename or update a tag
- 🚫 `DELETE /api/organizers/tags/{id}` - Delete a tag

### ✅ Foods (2/7 implemented)

**Implemented:**
- ✅ `GET /api/foods` - Search and list foods used in recipe ingredients
- ✅ `GET /api/foods/{id}` - Fetch a single food entry by ID

**Not Implemented:**
- 🚫 `POST /api/foods` - Add a new food to the ingredient food library
- 🚫 `PUT /api/foods/{id}` - Update a food entry's name or attributes
- 🚫 `DELETE /api/foods/{id}` - Remove a food from the library
- 🚫 `GET /api/foods/empty` - List foods not referenced by any recipe ingredient
- 🚫 `MERGE /api/foods/merge` - Merge duplicate food entries into one canonical entry

### ✅ Meal Plans (4/7 implemented)

**Implemented:**
- ✅ `GET /api/households/mealplans` - List all meal plan entries across a date range
- ✅ `GET /api/households/mealplans/today` - Fetch all meal plan entries scheduled for today
- ✅ `POST /api/households/mealplans` - Add a recipe to the meal plan on a specific date
- ✅ Bulk creation via loop — create multiple meal plan entries by repeating single-entry creation

**Not Implemented:**
- 🚫 `GET /api/households/mealplans/{id}` - Fetch a single meal plan entry by ID
- 🚫 `PUT /api/households/mealplans/{id}` - Update a meal plan entry's date or recipe assignment
- 🚫 `DELETE /api/households/mealplans/{id}` - Remove an entry from the meal plan

### ❌ Recipe Advanced Features (0 implemented)

- 🚫 `GET /api/recipes/{slug}/comments` - List all comments on a recipe
- 🚫 `POST /api/recipes/{slug}/comments` - Post a comment on a recipe
- 🚫 `GET /api/recipes/timeline` - View a chronological activity feed across all recipes
- 🚫 `GET /api/recipes/{slug}/share` - List public share links for a recipe
- 🚫 `POST /api/recipes/{slug}/share` - Create a public share link for a recipe
- 🚫 `GET /api/recipes/{slug}/exports` - Download a recipe in a supported export format (JSON, PDF, etc.)
- 🚫 `GET /api/households/recipe-parser` - Fetch the household's recipe scraper/parser configuration
- 🚫 `PUT /api/households/recipe-parser` - Update which parser Mealie uses when scraping recipes from URLs

### ❌ Household Management (0 implemented)

- 🚫 `GET /api/households/cookbooks` - List cookbooks (curated recipe collections) in the household
- 🚫 `POST /api/households/cookbooks` - Create a new cookbook with a filtered set of recipes
- 🚫 `GET /api/households/webhooks` - List outbound webhooks configured for the household
- 🚫 `POST /api/households/webhooks` - Create a webhook that fires on meal plan events
- 🚫 `GET /api/households/event-notifications` - List configured notification targets (Apprise URLs, etc.)
- 🚫 `POST /api/households/event-notifications` - Add a new event notification target
- 🚫 `GET /api/households/recipe-actions` - List custom recipe actions (external integrations triggered per recipe)
- 🚫 `POST /api/households/recipe-actions` - Add a new custom recipe action

### ❌ Organizer Extras (0 implemented)

- 🚫 `GET /api/organizers/tools` - List cooking tools used to tag which equipment a recipe requires
- 🚫 `POST /api/organizers/tools` - Add a new cooking tool to the organizer library
- 🚫 `GET /api/organizers/units` - List units of measurement used in recipe ingredient quantities
- 🚫 `POST /api/organizers/units` - Add a new unit of measurement
- 🚫 `GET /api/organizers/labels` - List labels used to categorize and sort shopping list items
- 🚫 `POST /api/organizers/labels` - Create a new shopping list label

### ❌ Admin & User Management (0 implemented)

- 🚫 `GET /api/admin/users` - List all user accounts in the instance (admin only)
- 🚫 `POST /api/admin/users` - Create a new user account (admin only)
- 🚫 `GET /api/groups` - List all groups in the instance
- 🚫 `POST /api/groups` - Create a new group
- 🚫 `GET /api/users/self` - Fetch the currently authenticated user's profile
- 🚫 `PATCH /api/users/self` - Update the current user's profile and preferences
- 🚫 `POST /api/auth/token` - Obtain an API token by exchanging username and password credentials
- 🚫 `POST /api/auth/refresh` - Refresh an expired API token
