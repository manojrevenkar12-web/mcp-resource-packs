/** Where the workspace comes from: a snapshot file (tests, demos) or the Smartsheet REST API (a customer). */
import { readFile } from "node:fs/promises";
import type { Sheet, Workspace } from "./types.js";

export interface Source {
  workspace(): Promise<Workspace>;
}

export class SnapshotSource implements Source {
  constructor(private readonly path: string) {}
  async workspace(): Promise<Workspace> {
    return JSON.parse(await readFile(this.path, "utf8")) as Workspace;
  }
}

type Fetch = typeof fetch;

/**
 * Reads sheets through Smartsheet API 2.0 with the customer's own token, so the user's permissions apply.
 * Sheets are re-read after `ttlMs`; a failed sheet read keeps the last good copy rather than dropping the sheet.
 */
export class SmartsheetSource implements Source {
  private cache: { at: number; ws: Workspace } | null = null;

  constructor(
    private readonly token: string,
    private readonly customer: string,
    private readonly opts: { base?: string; ttlMs?: number; fetch?: Fetch; now?: () => number } = {},
  ) {}

  private async get<T>(path: string): Promise<T> {
    const f = this.opts.fetch ?? fetch;
    const res = await f(`${this.opts.base ?? "https://api.smartsheet.com/2.0"}${path}`, {
      headers: { Authorization: `Bearer ${this.token}`, Accept: "application/json" },
    });
    if (!res.ok) throw new Error(`Smartsheet ${path}: HTTP ${res.status}`);
    return (await res.json()) as T;
  }

  async workspace(): Promise<Workspace> {
    const now = (this.opts.now ?? Date.now)();
    if (this.cache && now - this.cache.at < (this.opts.ttlMs ?? 60_000)) return this.cache.ws;
    const list = await this.get<{ data: { id: number; name: string }[] }>("/sheets?includeAll=true");
    const previous = new Map((this.cache?.ws.sheets ?? []).map((s) => [s.id, s]));
    const sheets: Sheet[] = [];
    for (const s of list.data) {
      try {
        sheets.push(await this.get<Sheet>(`/sheets/${s.id}`));
      } catch (e) {
        const old = previous.get(s.id);
        if (old) sheets.push(old);
        else throw e;
      }
    }
    const ws = { customer: this.customer, sheets };
    this.cache = { at: now, ws };
    return ws;
  }
}
