MCP_PORT ?= 3001

.PHONY: mcp-dev mcp-prod

mcp-dev: _check-port ## Start MCP server (local kandidat)
	@cd mcp && KANDIDAT_API_URL=http://localhost:8000 MCP_PORT=$(MCP_PORT) pnpm dev || true

# Caddy fronts kandidat.internal with its own internal CA, and Node's fetch
# (undici) does not read the OS trust store on its own -- --use-system-ca makes
# it do so (Node >= 22.15). If this fails with UNABLE_TO_GET_ISSUER_CERT_LOCALLY,
# the Caddy root is not imported on this machine: see step 3 of
# homelab/caddy/docs/runbook-https-internal.md.
mcp-prod: _check-port ## Start MCP server (prod dockhost)
	@cd mcp && KANDIDAT_API_URL=https://kandidat.internal NODE_OPTIONS=--use-system-ca MCP_PORT=$(MCP_PORT) pnpm dev || true

_check-port:
	@if ss -tlnp 2>/dev/null | grep -q ':$(MCP_PORT) '; then \
		echo "Error: port $(MCP_PORT) is already in use"; \
		ss -tlnp 2>/dev/null | grep ':$(MCP_PORT) '; \
		exit 1; \
	fi
