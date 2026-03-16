/**
 * MCP tools for candidatures (job applications).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiGet } from "../client.js";

export function registerCandidatureReadTools(server: McpServer): void {
  server.registerTool(
    "list_candidatures",
    {
      title: "List Job Applications",
      description:
        "List all job applications with optional filters by status, type, priority, or company category. " +
        "Returns an array of applications with their key fields (slug, entreprise, poste, statut, priorite, dates, etc.).",
      inputSchema: z.object({
        statut: z
          .optional(
            z.enum([
              "brouillon",
              "envoyee",
              "relancee",
              "entretien",
              "acceptee",
              "refusee",
              "sans-reponse",
              "archivee",
            ])
          )
          .describe("Filter by application status"),
        type: z
          .optional(z.enum(["offre", "spontanee"]))
          .describe("Filter by application type"),
        priorite: z
          .optional(z.enum(["haute", "moyenne", "basse"]))
          .describe("Filter by priority level"),
        categorie: z
          .optional(
            z.enum(["entreprise", "esn", "cabinet", "groupe", "organisation"])
          )
          .describe("Filter by company category"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ statut, type, priorite, categorie }) => {
      const params: Record<string, string> = {};
      if (statut) params.statut = statut;
      if (type) params.type = type;
      if (priorite) params.priorite = priorite;
      if (categorie) params.categorie = categorie;

      const data = await apiGet("/api/candidatures", params);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "get_candidature",
    {
      title: "Get Job Application Details",
      description:
        "Get complete details of a specific job application by its slug identifier, " +
        "including attached files, company info, status, dates, and content.",
      inputSchema: z.object({
        slug: z.string().describe("Kebab-case identifier (e.g. 'datadog', 'ovh-cloud')"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ slug }) => {
      const data = await apiGet(`/api/candidatures/${encodeURIComponent(slug)}`);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "get_candidature_history",
    {
      title: "Get Status Change Timeline",
      description:
        "Get the status change timeline for a job application: every transition " +
        "with its date, previous status, new status, and optional comment.",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ slug }) => {
      const data = await apiGet(
        `/api/candidatures/${encodeURIComponent(slug)}/historique`
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
