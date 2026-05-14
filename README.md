# Mealie MCP Server

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for [Mealie](https://github.com/mealie-recipes/mealie) that lets AI assistants like Claude and ChatGPT read your recipe database, manage shopping lists, and create meal plans — served over HTTP and secured with OAuth 2.0.

> **Origin:** This project is based on [rldiao/mealie-mcp-server](https://github.com/rldiao/mealie-mcp-server). It extends that work with OAuth 2.0 bearer authentication via [Authentik](https://goauthentik.io/), Docker/HTTP transport support, and removes recipe write tools (create, update, delete). See [CHANGELOG.md](CHANGELOG.md) for the full list of changes.

## ✨ Features

### 🔐 Single-User OAuth 2.0 Authentication (optional)
- **Authentik integration**: Validates bearer tokens via OIDC discovery + JWKS
- **Opt-in**: runs unauthenticated when `AUTHENTIK_ISSUER` is not set
- **Docker-friendly**: supports internal JWKS fetching via `AUTHENTIK_JWKS_URI` + `AUTHENTIK_HOST`

### 🍽️ Recipe Management
- **Advanced Search**: Filter by text, categories, tags, and tools with AND/OR logic
- **Metadata Tracking**: Mark recipes as made, track last made dates

### 🛒 Shopping Lists
- **List Management**: Create, update, and delete shopping lists
- **Item Operations**: Add, update, check off, and remove items
- **Bulk Operations**: Create, update, or delete multiple items at once
- **Recipe Integration**: Automatically add recipe ingredients to shopping lists

### 🏷️ Organization (read-only)
- **Categories**: Organize recipes with categories (Breakfast, Dinner, etc.)
- **Tags**: Tag recipes for easy filtering (Quick, Healthy, Family Favorite)
- **Advanced Filtering**: Search and filter with full pagination support
- **Empty Detection**: Find unused categories and tags

### 📅 Meal Planning
- **Meal Plans**: View and manage meal plans
- **Bulk Creation**: Add multiple meals at once
- **Today's Menu**: Quick access to today's planned meals

## 🚀 Installation

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- A running [Mealie](https://github.com/mealie-recipes/mealie) instance with an API key
- An [Authentik](https://goauthentik.io/) instance with a provider, app, and user configured (only required if using OAuth)

### Step 1 — Clone the repository

```bash
git clone <repository-url>
cd mealie-mcp-server
```

### Step 2 — Configure environment

```bash
cp .env.template .env
# Edit .env with your values
```

Set the variables in `.env`. The `AUTHENTIK_JWKS_URI` + `AUTHENTIK_HOST` pair is only needed if Authentik and this server share a Docker network — it lets the server fetch signing keys from the internal address rather than going through the public domain (more efficient, avoids hairpin NAT issues).

### Step 3 — Start the server

```bash
docker compose up -d
```

The server listens on port `8000` at `/mcp`. Configure your MCP client to connect to `http://your-host:8000/mcp` (or via a reverse proxy with TLS).

### OAuth / Authentik Setup (optional)

Authentication is opt-in. If `AUTHENTIK_ISSUER` is not set, the server starts without any authentication — useful for local testing.

When enabled, the server validates OAuth 2.0 bearer tokens issued by [Authentik](https://goauthentik.io/). Here is how the flow works in plain terms: your MCP client (Claude, ChatGPT, etc.) redirects you to your Authentik login page, you log in, and Authentik issues a token. The MCP server checks that token on every request to confirm who you are. Your Mealie API key never leaves the server.

#### Step 1 — Create a Provider in Authentik

In the Authentik admin UI go to **Applications → Providers → Create → OAuth2/OpenID Provider**.

| Field | Value |
|---|---|
| Name | `mealie-mcp-server` |
| Authorization flow | `default-provider-authorization-explicit-consent (Authorize Application)` |
| Client type | `Confidential` |
| Redirect URIs | Your MCP client's callback URL (see your client's OAuth setup docs)|
| Signing Key | Select any existing certificate, or create one under **System → Certificates** |

Callback URI examples:
`strict: https://claude.ai/api/mcp/auth_callback`
`strict: https://chatgpt.com/connector/oauth/<your-connector-id>`

Save the provider. On the detail page, note the **OpenID Configuration Issuer** URL — it looks like:

```
https://auth.your-domain.com/application/o/mealie-mcp-server/
```

This is your `AUTHENTIK_ISSUER` value.

#### Step 2 — Create an Application in Authentik

Go to **Applications → Applications → Create**.

| Field | Value |
|---|---|
| Name | `Mealie MCP Server` |
| Slug | `mealie-mcp-server` |
| Provider | Select the provider you just created |

Save.

#### Step 3 — Create and Assign a User

By default, all Authentik users can access the application. To restrict access, create a user and open the application → **Policy / Group / User Bindings** tab → **Bind existing policy/group/user** and add the specific users or groups you want to allow.

### Project Structure

```
mealie-mcp-server/
├── src/
│   ├── mealie/              # API client mixins
│   │   ├── client.py        # Base HTTP client
│   │   ├── recipe.py        # Recipe operations
│   │   ├── shopping_list.py # Shopping list operations
│   │   ├── categories.py    # Category operations
│   │   ├── tags.py          # Tag operations
│   │   ├── mealplan.py      # Meal plan operations
│   │   ├── foods.py         # Food operations
│   │   └── __init__.py      # MealieFetcher aggregator
│   ├── tools/               # MCP tool definitions
│   │   ├── recipe_tools.py
│   │   ├── shopping_list_tools.py
│   │   ├── categories_tools.py
│   │   ├── tags_tools.py
│   │   ├── mealplan_tools.py
│   │   ├── foods_tools.py
│   │   └── __init__.py
│   ├── models/              # Pydantic models
│   │   ├── mealplan.py
│   │   └── recipe.py
│   ├── auth.py              # OAuth/JWT verification (Authentik)
│   ├── server.py            # MCP server entry point
│   ├── prompts.py           # Server prompts
│   └── utils.py             # Shared utilities
├── Dockerfile
├── docker-compose.yml
├── .env.template
├── CHANGELOG.md
└── README.md
```

## 📚 Important Notes

### Filtering by Tags/Categories

When filtering recipes, you **must use slugs or UUIDs**, not display names:

✅ **Correct:**
```
"Get recipes with tags=['quick-meals', 'healthy']"
```

❌ **Incorrect:**
```
"Get recipes with tags=['Quick Meals', 'Healthy']"
```

Use `get_tags()` or `get_categories()` first to find the correct slugs.

### Field Preservation

When updating shopping list items, the server automatically preserves all existing fields. You only need to specify the fields you want to change:

```
# Only updates 'checked' field, preserves note, quantity, etc.
update_shopping_list_item(item_id="...", checked=True)
```

## 🐛 Known Issues

None known. Tested end-to-end with Claude and ChatGPT.

## 🔄 Changelog

See [CHANGELOG.md](CHANGELOG.md) for a detailed list of changes and version history.


## 🔮 Future Enhancements

- **Multi-user support (step 1)**: Store each user's Mealie API key as an attribute in Authentik and include it in the JWT via a property mapping — each user brings their own key, no admin involvement
- **Multi-user support (step 2)**: Configure Mealie as an OAuth provider backed by Authentik and implement OAuth token exchange (RFC 8693) — eliminating API keys entirely

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Credits

- Based on the original [mealie-mcp-server](https://github.com/rldiao/mealie-mcp-server) by [@rldiao](https://github.com/rldiao)
- [Mealie](https://github.com/mealie-recipes/mealie) - The recipe management system
- [FastMCP](https://github.com/jlowin/fastmcp) - The MCP framework

## 📞 Support

For issues and questions:
- Check the [CHANGELOG.md](CHANGELOG.md) for recent updates
- Review the [Mealie API documentation](https://docs.mealie.io)
- Open an issue on GitHub

## 🔗 Related Links

- [Mealie Documentation](https://docs.mealie.io)
- [MCP Protocol Specification](https://modelcontextprotocol.io)
- [Authentik](https://goauthentik.io/)
