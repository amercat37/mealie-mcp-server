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

> **Note:** Recipe, category, and tag write tools were intentionally removed to limit the blast radius of an exposed MCP endpoint. See CHANGELOG.md for the full list of removed tools.

## Detailed Coverage

### ✅ Recipe Operations (4/20 implemented)

**Implemented:**
- ✅ `GET /api/recipes` - List/search recipes with advanced filtering
- ✅ `GET /api/recipes/{slug}` - Get recipe details (detailed)
- ✅ `GET /api/recipes/{slug}` - Get recipe summary (concise)
- ✅ `PATCH /api/recipes/{slug}/last-made` - Update last made

**Removed (intentionally — read-only policy):**
- 🚫 `POST /api/recipes` - Create recipe
- 🚫 `PUT /api/recipes/{slug}` - Update recipe (full)
- 🚫 `PATCH /api/recipes/{slug}` - Partial update
- 🚫 `DELETE /api/recipes/{slug}` - Delete recipe
- 🚫 `POST /api/recipes/{slug}/duplicate` - Duplicate recipe
- 🚫 `POST /api/recipes/{slug}/image` - Scrape image from URL
- 🚫 `PUT /api/recipes/{slug}/image` - Upload image file
- 🚫 `POST /api/recipes/{slug}/assets` - Upload asset file

**Not Implemented:**
- ⏳ `POST /api/recipes/create/url` - Create from URL
- ⏳ `POST /api/recipes/create/url/bulk` - Bulk create from URLs
- ⏳ `POST /api/recipes/create/zip` - Create from ZIP
- ⏳ `POST /api/recipes/create/html-or-json` - Create from HTML/JSON
- ⏳ `PUT /api/recipes` - Bulk update
- ⏳ `PATCH /api/recipes` - Bulk patch

### ✅ Shopping Lists (13/17 implemented)

**Shopping List Management:**
- ✅ `GET /api/households/shopping/lists` - List all
- ✅ `POST /api/households/shopping/lists` - Create
- ✅ `GET /api/households/shopping/lists/{id}` - Get by ID
- ✅ `DELETE /api/households/shopping/lists/{id}` - Delete

**Recipe Integration:**
- ✅ `POST /api/households/shopping/lists/{id}/recipe/{recipe_id}` - Add recipe
- ✅ `POST /api/households/shopping/lists/{id}/recipe/{recipe_id}/delete` - Remove recipe

**Shopping List Items:**
- ✅ `GET /api/households/shopping/items` - List all items
- ✅ `GET /api/households/shopping/items/{id}` - Get item
- ✅ `POST /api/households/shopping/items` - Create item
- ✅ `POST /api/households/shopping/items/create-bulk` - Bulk create
- ✅ `PUT /api/households/shopping/items/{id}` - Update item
- ✅ `PUT /api/households/shopping/items` - Bulk update
- ✅ `DELETE /api/households/shopping/items/{id}` - Delete item
- ✅ `DELETE /api/households/shopping/items` - Bulk delete (query params)

**Not Implemented:**
- ⏳ `PUT /api/households/shopping/lists/{id}` - Update list
- ⏳ `PUT /api/households/shopping/lists/{id}/label-settings` - Update label settings
- ⏳ `POST /api/households/shopping/lists/{id}/recipe` - Add multiple recipes (array payload)

### ✅ Categories (4/7 implemented — read-only)

- ✅ `GET /api/organizers/categories` - List all
- ✅ `GET /api/organizers/categories/empty` - Get empty
- ✅ `GET /api/organizers/categories/{id}` - Get by ID
- ✅ `GET /api/organizers/categories/slug/{slug}` - Get by slug
- 🚫 `POST /api/organizers/categories` - Create (removed — read-only policy)
- 🚫 `PUT /api/organizers/categories/{id}` - Update (removed — read-only policy)
- 🚫 `DELETE /api/organizers/categories/{id}` - Delete (removed — read-only policy)

### ✅ Tags (4/7 implemented — read-only)

- ✅ `GET /api/organizers/tags` - List all
- ✅ `GET /api/organizers/tags/empty` - Get empty
- ✅ `GET /api/organizers/tags/{id}` - Get by ID
- ✅ `GET /api/organizers/tags/slug/{slug}` - Get by slug
- 🚫 `POST /api/organizers/tags` - Create (removed — read-only policy)
- 🚫 `PUT /api/organizers/tags/{id}` - Update (removed — read-only policy)
- 🚫 `DELETE /api/organizers/tags/{id}` - Delete (removed — read-only policy)

### 🔶 Foods (2/7 implemented — read-only)

- ✅ `GET /api/foods` - List/search foods
- ✅ `GET /api/foods/{id}` - Get food by ID
- ⏳ `POST /api/foods` - Create food
- ⏳ `PUT /api/foods/{id}` - Update food
- ⏳ `DELETE /api/foods/{id}` - Delete food
- ⏳ `GET /api/foods/empty` - Get empty foods
- ⏳ `MERGE /api/foods/merge` - Merge foods

### 🔶 Meal Plans (4/7 implemented)

**Implemented:**
- ✅ `GET /api/households/mealplans` - List meal plans
- ✅ `GET /api/households/mealplans/today` - Get today's plan
- ✅ `POST /api/households/mealplans` - Create entry
- ✅ Bulk creation via loop (not native bulk endpoint)

**Not Implemented:**
- ⏳ `GET /api/households/mealplans/{id}` - Get by ID
- ⏳ `PUT /api/households/mealplans/{id}` - Update entry
- ⏳ `DELETE /api/households/mealplans/{id}` - Delete entry

### ❌ Recipe Advanced Features (0 implemented)

- ⏳ `GET/POST /api/recipes/{slug}/comments` - Recipe comments
- ⏳ `GET /api/recipes/timeline` - Recipe timeline
- ⏳ `GET/POST /api/recipes/{slug}/share` - Recipe sharing
- ⏳ `GET /api/recipes/{slug}/exports` - Recipe exports
- ⏳ Recipe scraper settings

### ❌ Household Management (0 implemented)

- ⏳ `GET/POST /api/households/cookbooks` - Cookbooks
- ⏳ `GET/POST /api/households/webhooks` - Webhooks
- ⏳ `GET/POST /api/households/event-notifications` - Event notifications
- ⏳ `GET/POST /api/households/recipe-actions` - Recipe actions

### ❌ Organizer Extras (0 implemented)

- ⏳ `GET/POST /api/organizers/tools` - Tools
- ⏳ `GET/POST /api/organizers/units` - Units
- ⏳ `GET/POST /api/organizers/labels` - Labels

### ❌ Admin & User Management (0 implemented)

- ⏳ `GET/POST /api/admin/users` - User administration
- ⏳ `GET/POST /api/groups` - Group management
- ⏳ `GET/PATCH /api/users/self` - User profiles
- ⏳ Authentication endpoints

