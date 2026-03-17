/**
 * MCP tools for candidatures (job applications).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiGet, apiPost, apiPut, apiPatch, apiDelete } from "../client.js";

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

export function registerCandidatureWriteTools(server: McpServer): void {
  server.registerTool(
    "create_candidature",
    {
      title: "Create Job Application",
      description:
        "Create a new job application linked to an existing target company. " +
        "Status starts as 'brouillon'. The company category is derived automatically from the cible. " +
        "You must provide a valid cible_id — use list_cibles first to find it.",
      inputSchema: z.object({
        entreprise: z.string().describe("Company name (becomes the slug in kebab-case)"),
        poste: z.optional(z.string()).describe("Job title"),
        type: z
          .optional(z.enum(["offre", "spontanee"]))
          .describe("Application type (default: offre)"),
        localisation: z.optional(z.string()).describe("Job location"),
        priorite: z
          .optional(z.enum(["haute", "moyenne", "basse"]))
          .describe("Priority level (default: moyenne)"),
        cible_id: z.number().int().describe("Target company ID (must exist)"),
        contenu: z
          .optional(z.string())
          .describe("Markdown content: job description, notes, URL"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async (input) => {
      const data = await apiPost("/api/candidatures", input);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "update_candidature",
    {
      title: "Update Job Application",
      description:
        "Update one or more fields on an existing job application. " +
        "Can change status (must follow the state machine transitions), priority, dates, content, etc. " +
        "If changing status, you can include a commentaire explaining the transition. " +
        "Status transitions: brouillon->envoyee->relancee->entretien->acceptee/refusee, any->archivee (terminal).",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
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
          .describe("New status (must be a valid transition from current)"),
        priorite: z
          .optional(z.enum(["haute", "moyenne", "basse"]))
          .describe("New priority level"),
        categorie_entreprise: z
          .optional(
            z.enum(["entreprise", "esn", "cabinet", "groupe", "organisation"])
          )
          .describe("Company category override"),
        date_candidature: z
          .optional(z.string())
          .describe("Application date (YYYY-MM-DD)"),
        date_relance: z
          .optional(z.string())
          .describe("Follow-up date (YYYY-MM-DD)"),
        entreprise: z.optional(z.string()).describe("Company name"),
        poste: z.optional(z.string()).describe("Job title"),
        type: z
          .optional(z.enum(["offre", "spontanee"]))
          .describe("Application type"),
        localisation: z.optional(z.string()).describe("Location"),
        contenu: z.optional(z.string()).describe("Markdown content"),
        commentaire: z
          .optional(z.string())
          .describe("Comment for status change (ignored if status unchanged)"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ slug, ...fields }) => {
      const body: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(fields)) {
        if (value !== undefined) body[key] = value;
      }
      const data = await apiPut(
        `/api/candidatures/${encodeURIComponent(slug)}`,
        body
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "update_historique_comment",
    {
      title: "Edit Status Change Comment",
      description:
        "Add or edit a comment on a specific status change in a candidature's history timeline.",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
        historique_id: z.number().int().describe("History entry ID"),
        commentaire: z.string().max(1000).describe("Comment text (max 1000 chars)"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: true,
      },
    },
    async ({ slug, historique_id, commentaire }) => {
      const data = await apiPatch(
        `/api/candidatures/${encodeURIComponent(slug)}/historique/${historique_id}`,
        { commentaire }
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "delete_candidature",
    {
      title: "Delete Job Application",
      description:
        "Permanently delete a job application and all its attached files from disk. " +
        "THIS CANNOT BE UNDONE. The target company will be marked as 'not contacted' " +
        "if this was its last active application.",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: true,
        idempotentHint: true,
      },
    },
    async ({ slug }) => {
      const data = await apiDelete(
        `/api/candidatures/${encodeURIComponent(slug)}`
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
