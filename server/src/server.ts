/** The MCP server one customer's AI tools connect to: their pack as resources, and a query tool that answers with code. */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { glossaryText, rulesText, semantics } from "./describe.js";
import { answer } from "./engine.js";
import type { Source } from "./source.js";
import type { Pack, Query } from "./types.js";

export type Options = { today?: () => string };

const where = z
  .object({
    project: z.string().optional().describe("project (sheet) name, exactly as listed"),
    owner: z.string().optional().describe("assignee, exactly as in the sheet"),
    overdue: z.boolean().optional(),
    at_risk: z.boolean().optional().describe("at risk by this customer's rule (see pack://rules)"),
    done: z.boolean().optional(),
    due_within_days: z.number().int().min(0).max(365).optional(),
    fiscal_quarter: z.literal("current").optional(),
  })
  .strict();

export function createServer(pack: Pack, source: Source, opts: Options = {}): McpServer {
  const today = opts.today ?? (() => new Date().toISOString().slice(0, 10));
  const server = new McpServer({ name: `resource-pack-${pack.customer}`, version: "0.1.0" });

  server.registerResource(
    "rules",
    "pack://rules",
    { title: "How this customer runs projects", mimeType: "text/markdown", description: "At risk, done, milestones, fiscal year" },
    async (uri) => ({ contents: [{ uri: uri.href, mimeType: "text/markdown", text: rulesText(pack) }] }),
  );
  server.registerResource(
    "glossary",
    "pack://glossary",
    { title: "The customer's own words", mimeType: "text/markdown" },
    async (uri) => ({ contents: [{ uri: uri.href, mimeType: "text/markdown", text: glossaryText(pack) }] }),
  );
  server.registerResource(
    "semantics",
    "pack://semantics",
    { title: "What every column means, per sheet template", mimeType: "application/json" },
    async (uri) => {
      const ws = await source.workspace();
      const names = new Map(ws.sheets.map((s) => [String(s.id), s.name]));
      return { contents: [{ uri: uri.href, mimeType: "application/json", text: JSON.stringify(semantics(pack, names)) }] };
    },
  );

  server.registerTool(
    "portfolio_query",
    {
      title: "Answer a portfolio question",
      description:
        "Counts, lists, average completion or busiest assignee across this customer's live project plans, computed " +
        "by code with the customer's own column meanings and rules. Use it instead of reading rows.",
      inputSchema: {
        op: z.enum(["count", "list", "avg_progress", "top_owner"]),
        entity: z.enum(["tasks", "milestones", "projects"]),
        where: where.optional(),
      },
      annotations: { readOnlyHint: true },
    },
    async (args) => {
      const ws = await source.workspace();
      const q = args as Query;
      if (q.where?.project && !ws.sheets.some((s) => s.name === q.where!.project && pack.sheets[String(s.id)]?.kind === "project")) {
        const live = ws.sheets.filter((s) => pack.sheets[String(s.id)]?.kind === "project").map((s) => s.name);
        return { isError: true, content: [{ type: "text", text: `No live project named "${q.where.project}". Live projects: ${live.join(", ")}` }] };
      }
      const result = answer(ws, pack, q, today());
      return {
        content: [{ type: "text", text: JSON.stringify({ answer: result, query: q, as_of: today() }) }],
        structuredContent: { answer: result as unknown as Record<string, unknown>, as_of: today() },
      };
    },
  );

  server.registerPrompt(
    "weekly_portfolio_review",
    { title: "Weekly portfolio review", description: "The questions this customer asks every Monday" },
    async () => ({
      messages: [
        {
          role: "user",
          content: {
            type: "text",
            text:
              "Read pack://rules and pack://glossary, then use portfolio_query to answer: which projects are at risk, " +
              "how many tasks are overdue, which milestones are due this quarter, and who has the most open tasks due in " +
              "the next 14 days. Give numbers, not estimates.",
          },
        },
      ],
    }),
  );
  return server;
}
