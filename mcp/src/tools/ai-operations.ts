/**
 * MCP tools for AI-powered operations (cible enrichment, CV adaptation).
 */

import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import * as z from "zod/v4";
import { apiPost } from "../client.js";

export function registerAiOperationTools(server: McpServer): void {
  server.registerTool(
    "enrich_cible",
    {
      title: "Enrich Target Company (AI)",
      description:
        "Trigger AI-powered enrichment for a target company: searches the web (Tavily) " +
        "for company info (website, LinkedIn, sector) and contacts (leadership, team members), " +
        "then returns suggestions. Does NOT modify the company — use apply_enrichment to save changes. " +
        "Requires Tavily and LLM to be configured in settings.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async ({ cible_id }) => {
      const data = await apiPost(`/api/cibles/${cible_id}/enrich`);
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "apply_enrichment",
    {
      title: "Apply Enrichment Suggestions",
      description:
        "Apply selected enrichment suggestions to update a target company's information " +
        "and optionally create new contacts. Takes the output from enrich_cible and applies " +
        "the fields you want to keep.",
      inputSchema: z.object({
        cible_id: z.number().int().describe("Target company ID"),
        accepted: z
          .record(z.string(), z.unknown())
          .describe("Selected fields and contacts from enrichment result to apply"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async ({ cible_id, accepted }) => {
      const data = await apiPost(`/api/cibles/${cible_id}/enrich/apply`, {
        accepted,
      });
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "adapt_cv",
    {
      title: "Adapt CV for Application (AI)",
      description:
        "Generate an AI-adapted version of your CV for a specific job application. " +
        "Uses the configured LLM to tailor the CV based on the job posting content. " +
        "Returns HTML — use save_adapted_cv to persist as PDF+DOCX. " +
        "Requires LLM and CV reference to be configured in settings.",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
        cv_source: z
          .optional(z.enum(["auto", "global", "candidature"]))
          .describe("CV source: auto (default), global reference, or candidature-specific"),
      }),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async ({ slug, cv_source }) => {
      const body: Record<string, string> = {};
      if (cv_source) body.cv_source = cv_source;
      const data = await apiPost(
        `/api/candidatures/${encodeURIComponent(slug)}/cv/adapt`,
        body
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );

  server.registerTool(
    "save_adapted_cv",
    {
      title: "Save Adapted CV (PDF + DOCX)",
      description:
        "Save an adapted CV as PDF and DOCX files attached to the job application. " +
        "Takes the HTML output from adapt_cv.",
      inputSchema: z.object({
        slug: z.string().describe("Candidature identifier"),
        adapted_html: z.string().describe("HTML content from adapt_cv result"),
      }),
      annotations: {
        readOnlyHint: false,
        destructiveHint: false,
        idempotentHint: false,
      },
    },
    async ({ slug, adapted_html }) => {
      const data = await apiPost(
        `/api/candidatures/${encodeURIComponent(slug)}/cv/save`,
        { adapted_html }
      );
      return {
        content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }],
      };
    }
  );
}
