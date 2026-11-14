import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { describe, expect, it } from "vitest";
import { answer } from "../src/engine.js";
import { createServer } from "../src/server.js";
import type { Source } from "../src/source.js";
import type { Pack, Workspace } from "../src/types.js";
import fixture from "./fixtures/conformance.json";

const raw = fixture as unknown as { today: string; workspaces: Record<string, Workspace>; packs: Record<string, Pack> };
const id = Object.keys(raw.workspaces)[0];
const f = { today: raw.today, workspace: raw.workspaces[id] };
const pack = raw.packs[`${id}:signed_off`];
const source: Source = { workspace: async () => f.workspace };
const live = f.workspace.sheets.filter((s) => pack.sheets[String(s.id)]?.kind === "project").map((s) => s.name);

async function connect() {
  const server = createServer(pack, source, { today: () => f.today });
  const [a, b] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test", version: "0" });
  await Promise.all([server.connect(a), client.connect(b)]);
  return client;
}

const text = (r: { content: unknown }) => (r.content as { type: string; text: string }[])[0].text;

describe("MCP server", () => {
  it("serves the pack as resources a client can list and read", async () => {
    const c = await connect();
    const uris = (await c.listResources()).resources.map((r) => r.uri).sort();
    expect(uris).toEqual(["pack://glossary", "pack://rules", "pack://semantics"]);
    const rules = await c.readResource({ uri: "pack://rules" });
    expect((rules.contents[0] as { text: string }).text).toMatch(/financial year starts/);
    const sem = JSON.parse((await c.readResource({ uri: "pack://semantics" })).contents[0].text as string);
    expect(sem.sheets.map((s: { sheet: string }) => s.sheet)).toEqual(expect.arrayContaining(live));
  });

  it("answers a portfolio query with the engine, read-only", async () => {
    const c = await connect();
    const tool = (await c.listTools()).tools.find((t) => t.name === "portfolio_query")!;
    expect(tool.annotations?.readOnlyHint).toBe(true);
    const q = { op: "count", entity: "tasks", where: { overdue: true } } as const;
    const r = await c.callTool({ name: "portfolio_query", arguments: q });
    expect(JSON.parse(text(r as { content: unknown })).answer).toBe(answer(f.workspace, pack, q, f.today));
  });

  it("names the live projects when asked about one that is not live", async () => {
    const c = await connect();
    const archived = f.workspace.sheets.find((s) => pack.sheets[String(s.id)]?.kind === "archive")!.name;
    const r = (await c.callTool({ name: "portfolio_query", arguments: { op: "count", entity: "tasks", where: { project: archived } } })) as {
      isError?: boolean;
      content: unknown;
    };
    expect(r.isError).toBe(true);
    expect(text(r)).toContain(live[0]);
  });

  it("rejects a filter the engine does not know", async () => {
    const c = await connect();
    const r = (await c.callTool({ name: "portfolio_query", arguments: { op: "count", entity: "tasks", where: { colour: "red" } } })) as {
      isError?: boolean;
    };
    expect(r.isError).toBe(true);
  });

  it("offers the weekly review prompt", async () => {
    const c = await connect();
    const p = await c.getPrompt({ name: "weekly_portfolio_review" });
    expect(JSON.stringify(p.messages)).toContain("portfolio_query");
  });
});
