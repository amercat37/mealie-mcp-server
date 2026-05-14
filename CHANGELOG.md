# Changelog

All notable changes to this project will be documented here.

---

## [1.0.0] — 2026-05-12

Initial release.

### Features

- **31 MCP tools** covering recipes, shopping lists, categories (read-only), tags (read-only), foods (read-only), and meal plans
- **OAuth 2.0 bearer authentication** via [Authentik](https://goauthentik.io/) — JWT validation using OIDC discovery + JWKS; opt-in (server runs unauthenticated when `AUTHENTIK_ISSUER` is not set)
- **Docker + HTTP transport** — `Dockerfile` and `docker-compose.yml` for containerised deployment; server listens on port `8000` at `/mcp`
- **Read-only policy on categories and tags** — recipe write tools (create, update, delete) removed to limit the blast radius of an exposed MCP endpoint; shopping list and meal plan write tools retained as the primary interactive use case

### Origin

Based on [rldiao/mealie-mcp-server](https://github.com/rldiao/mealie-mcp-server). See [README.md](README.md) for the full list of changes from the original.
