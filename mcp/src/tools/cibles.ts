/**
 * MCP tools for cibles (target companies).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiGet, apiPost, apiPut, apiDelete } from "../client.js";

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

const CIBLE_CATEGORIES = z.enum([
  "grands-groupes",
  "esn",
  "entreprises",
  "cabinets",
  "organisations",
]);

export function registerCibleWriteTools(server: McpServer): void {
  server.registerTool(
    "create_cible",
    {
      title: "Add Target Company",
      description:
        "Add a new target company to track. You must specify a name and category. " +
        "The company will be added to the bottom of its category list.",
      inputSchema: z.object({
        nom: z.string().describe("Company name"),
        categorie: CIBLE_CATEGORIES.describe(
          "Company category"
        ),
        url: z.optional(z.string()).describe("Company website URL"),
        description: z.optional(z.string()).describe("Short description"),
        email: z.optional(z.string()).describe("General contact email"),
        linkedin: z.optional(z.string()).describe("LinkedIn company page URL"),
        inscrit_plateforme: z.optional(z.boolean()).describe("Registered on recruitment platform (cabinets only)"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async (input) => {
      const data = await apiPost("/api/cibles", input);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "update_cible",
    {
      title: "Update Target Company",
      description:
        "Update a target company's information: name, category, website, description, email, or LinkedIn URL.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
        nom: z.optional(z.string()).describe("New company name"),
        categorie: z.optional(CIBLE_CATEGORIES).describe("New category"),
        url: z.optional(z.string()).describe("Website URL"),
        description: z.optional(z.string()).describe("Description"),
        email: z.optional(z.string()).describe("Contact email"),
        linkedin: z.optional(z.string()).describe("LinkedIn URL"),
        inscrit_plateforme: z.optional(z.boolean()).describe("Registered on recruitment platform (cabinets only)"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ cible_id, ...fields }) => {
      const body: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(fields)) {
        if (value !== undefined) body[key] = value;
      }
      const data = await apiPut(`/api/cibles/${cible_id}`, body);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "delete_cible",
    {
      title: "Delete Target Company",
      description:
        "Delete a target company AND ALL its linked job applications and files. " +
        "THIS CASCADES AND CANNOT BE UNDONE. Use with extreme caution.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
      },
    },
    async ({ cible_id }) => {
      const data = await apiDelete(`/api/cibles/${cible_id}`);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
