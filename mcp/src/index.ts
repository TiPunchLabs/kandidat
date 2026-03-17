/**
 * kandidat MCP Server — entry point.
 *
 * Exposes kandidat's REST API as MCP tools and resources
 * so an LLM agent can manage job applications via natural language.
 *
 * Transport: streamable HTTP (stateless mode).
 * All business logic stays in the Flask API — this server is a semantic proxy.
 */

import { createServer } from "node:http";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/streamableHttp.js";

import { registerCandidatureReadTools, registerCandidatureWriteTools } from "./tools/candidatures.js";
import { registerCibleReadTools, registerCibleWriteTools } from "./tools/cibles.js";
import { registerContactTools } from "./tools/contacts.js";
import { registerSearchTools } from "./tools/search.js";
import { registerAiOperationTools } from "./tools/ai-operations.js";
import { registerEnumResources } from "./resources/enums.js";

const PORT = parseInt(process.env.MCP_PORT || "3001", 10);

function createMcpServer(): McpServer {
  const server = new McpServer({
    name: "kandidat",
    version: "0.1.0",
  });

  // Register all tools
  registerCandidatureReadTools(server);
  registerCandidatureWriteTools(server);
  registerCibleReadTools(server);
  registerCibleWriteTools(server);
  registerContactTools(server);
  registerSearchTools(server);
  registerAiOperationTools(server);

  // Register resources
  registerEnumResources(server);

  return server;
}

// Stateless HTTP server: one MCP server instance per request
const httpServer = createServer(async (req, res) => {
  // Health check
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ status: "ok" }));
    return;
  }

  // MCP endpoint
  if (req.method === "POST" && req.url === "/mcp") {
    const server = createMcpServer();
    const transport = new StreamableHTTPServerTransport({
      sessionIdGenerator: undefined, // stateless
    });
    await server.connect(transport);

    // Read request body
    const chunks: Buffer[] = [];
    for await (const chunk of req) {
      chunks.push(chunk as Buffer);
    }
    const body = JSON.parse(Buffer.concat(chunks).toString());

    await transport.handleRequest(req, res, body);
    return;
  }

  // 404 for everything else
  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ error: "Not found" }));
});

httpServer.listen(PORT, "127.0.0.1", () => {
  console.log(`kandidat MCP server listening on http://127.0.0.1:${PORT}/mcp`);
  console.log(
    `kandidat API target: ${process.env.KANDIDAT_API_URL || "http://localhost:8000"}`
  );
});
