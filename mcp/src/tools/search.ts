/**
 * MCP tools for search and statistics.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiGet } from "../client.js";

export function registerSearchTools(server: McpServer): void {
  server.registerTool(
    "search_candidatures",
    {
      title: "Search Job Applications",
      description:
        "Full-text search across all job applications. Searches company name, " +
        "position, content, and attached file names.",
      inputSchema: z.object({
        query: z.string().describe("Search terms"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ query }) => {
      const data = await apiGet("/api/search", { q: query });
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "get_stats",
    {
      title: "Get Dashboard Statistics",
      description:
        "Get dashboard statistics: total application count, breakdowns by " +
        "status/type/priority/category, and chronological timeline of applications.",
      inputSchema: z.object({}),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async () => {
      const data = await apiGet("/api/stats");
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "get_settings",
    {
      title: "Get Application Settings",
      description:
        "Get current application settings: which LLM provider is configured, " +
        "whether a CV reference exists, Tavily API status.",
      inputSchema: z.object({}),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async () => {
      const data = await apiGet("/api/settings");
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
