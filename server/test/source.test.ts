import { describe, expect, it } from "vitest";
import { SmartsheetSource } from "../src/source.js";

function fakeFetch(fail: Set<number>, calls: string[]) {
  return (async (url: string, init?: RequestInit) => {
    calls.push(url);
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer t0k");
    if (url.endsWith("/sheets?includeAll=true")) return new Response(JSON.stringify({ data: [{ id: 1, name: "A" }, { id: 2, name: "B" }] }));
    const id = Number(url.split("/").pop());
    if (fail.has(id)) return new Response("", { status: 503 });
    return new Response(JSON.stringify({ id, name: id === 1 ? "A" : "B", columns: [], rows: [] }));
  }) as unknown as typeof fetch;
}

describe("SmartsheetSource", () => {
  it("reads every sheet with the customer's token and caches for the TTL", async () => {
    const calls: string[] = [];
    let now = 0;
    const s = new SmartsheetSource("t0k", "C1", { fetch: fakeFetch(new Set(), calls), ttlMs: 1000, now: () => now });
    expect((await s.workspace()).sheets.map((x) => x.name)).toEqual(["A", "B"]);
    await s.workspace();
    expect(calls.length).toBe(3);
    now = 2000;
    await s.workspace();
    expect(calls.length).toBe(6);
  });

  it("keeps the last good copy of a sheet that fails to load, and fails when there is none", async () => {
    const fail = new Set<number>();
    let now = 0;
    const s = new SmartsheetSource("t0k", "C1", { fetch: fakeFetch(fail, []), ttlMs: 10, now: () => now });
    await s.workspace();
    fail.add(2);
    now = 100;
    expect((await s.workspace()).sheets.map((x) => x.name)).toEqual(["A", "B"]);
    const fresh = new SmartsheetSource("t0k", "C1", { fetch: fakeFetch(fail, []) });
    await expect(fresh.workspace()).rejects.toThrow(/HTTP 503/);
  });
});
