# ADR-003: MCP server as stateless semantic proxy (TypeScript)

## Status

Accepted

## Context

kandidat needs to be controllable by LLM agents (e.g. Claude Desktop, Claude Code) via the Model Context Protocol (MCP). The existing REST API already contains all business logic and validation. The question was whether to embed MCP support in the Python application or run it as a separate service.

## Decision

Implement the MCP server as a separate TypeScript process in `mcp/`, using `@modelcontextprotocol/sdk`. The server acts as a **semantic proxy**: it exposes 23 MCP tools (8 read, 7 write, 3 delete, 5 AI operations) and enum resources, but contains zero business logic. Every tool simply maps to an HTTP call against the kandidat REST API.

Key design choices:
- **Transport**: Streamable HTTP (stateless mode) on port 3001, one MCP server instance per request.
- **API target**: Configurable via `KANDIDAT_API_URL` environment variable.
- **Validation**: Zod schemas for tool input parameters; all business validation enforced by the Flask API.
- **No session state**: `sessionIdGenerator: undefined` -- each request is independent.

## Consequences

- The MCP server can be deployed, scaled, and restarted independently from the Python API.
- Zero risk of business logic drift between REST API and MCP interface -- the API is the single source of truth.
- TypeScript was chosen because the MCP SDK is primarily JavaScript/TypeScript; no Python MCP SDK was mature at the time.
- Two runtimes to maintain (Python + Node.js), but the MCP server is thin (~500 lines total).
- Agent configuration is a single URL: `http://127.0.0.1:3001/mcp`.
