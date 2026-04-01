MCP_PORT ?= 3001

.PHONY: mcp-dev mcp-prod

mcp-dev: _check-port ## Start MCP server (local kandidat)
	@cd mcp && KANDIDAT_API_URL=http://localhost:8000 MCP_PORT=$(MCP_PORT) pnpm dev || true

mcp-prod: _check-port ## Start MCP server (prod dockhost)
	@cd mcp && KANDIDAT_API_URL=http://kandidat.internal MCP_PORT=$(MCP_PORT) pnpm dev || true

_check-port:
	@if ss -tlnp 2>/dev/null | grep -q ':$(MCP_PORT) '; then \
		echo "Error: port $(MCP_PORT) is already in use"; \
		ss -tlnp 2>/dev/null | grep ':$(MCP_PORT) '; \
		exit 1; \
	fi
