/**
 * MCP resources exposing kandidat enum values and business rules.
 * Loaded into the LLM context so it always knows valid values.
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { apiGet } from "../client.js";

// Cached enums — fetched once at first access, then reused
let cachedEnums: Record<string, unknown> | null = null;

async function getEnums(): Promise<Record<string, unknown>> {
  if (!cachedEnums) {
    cachedEnums = await apiGet<Record<string, unknown>>("/api/enums");
  }
  return cachedEnums;
}

export function registerEnumResources(server: McpServer): void {
  server.registerResource(
    "enums",
    "kandidat://enums",
    {
      title: "kandidat Enum Values & Business Rules",
      description:
        "All valid enum values (statuts, types, priorites, categories), " +
        "status transition rules, and cible-to-candidature category mapping. " +
        "Use this to know which values are accepted by create/update tools.",
      mimeType: "application/json",
    },
    async (uri) => {
      const enums = await getEnums();
      return {
        contents: [
          {
            uri: uri.href,
            mimeType: "application/json",
            text: JSON.stringify(enums, null, 2),
          },
        ],
      };
    }
  );
}
