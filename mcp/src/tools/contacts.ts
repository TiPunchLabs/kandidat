/**
 * MCP tools for contacts (people linked to target companies).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiPost, apiPut, apiDelete } from "../client.js";

export function registerContactTools(server: McpServer): void {
  server.registerTool(
    "create_contact",
    {
      title: "Add Contact to Company",
      description:
        "Add a contact person (recruiter, hiring manager, CTO...) to a target company.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
        nom: z.string().describe("Last name"),
        prenom: z.optional(z.string()).describe("First name"),
        email: z.optional(z.string()).describe("Email address"),
        telephone: z.optional(z.string()).describe("Phone number"),
        linkedin: z.optional(z.string()).describe("LinkedIn profile URL"),
        fonction: z.optional(z.string()).describe("Job title / role"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async ({ cible_id, ...fields }) => {
      const data = await apiPost(`/api/cibles/${cible_id}/contacts`, fields);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "update_contact",
    {
      title: "Update Contact",
      description: "Update a contact's information for a target company.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
        contact_id: z.number().int().describe("Contact ID"),
        nom: z.optional(z.string()).describe("Last name"),
        prenom: z.optional(z.string()).describe("First name"),
        email: z.optional(z.string()).describe("Email"),
        telephone: z.optional(z.string()).describe("Phone"),
        linkedin: z.optional(z.string()).describe("LinkedIn URL"),
        fonction: z.optional(z.string()).describe("Job title"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ cible_id, contact_id, ...fields }) => {
      const body: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(fields)) {
        if (value !== undefined) body[key] = value;
      }
      const data = await apiPut(
        `/api/cibles/${cible_id}/contacts/${contact_id}`,
        body
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "delete_contact",
    {
      title: "Delete Contact",
      description:
        "Delete a contact from a target company. Only removes the contact, " +
        "not the company or its applications.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
        contact_id: z.number().int().describe("Contact ID"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
      },
    },
    async ({ cible_id, contact_id }) => {
      const data = await apiDelete(
        `/api/cibles/${cible_id}/contacts/${contact_id}`
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
