/**
 * MCP tools for cibles (target companies).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiGet } from "../client.js";

export function registerCibleReadTools(server: McpServer): void {
  server.registerTool(
    "list_cibles",
    {
      title: "List Target Companies",
      description:
        "List all target companies grouped by category (grands-groupes, esn, entreprises, " +
        "cabinets, organisations). Each entry includes name, contacted status, and count of active applications.",
      inputSchema: z.object({}),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async () => {
      const data = await apiGet("/api/cibles");
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "get_cible_detail",
    {
      title: "Get Target Company Details",
      description:
        "Get a target company's full details: name, category, website, description, " +
        "contacts list, and all linked active job applications.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ cible_id }) => {
      const data = await apiGet(`/api/cibles/${cible_id}/detail`);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
