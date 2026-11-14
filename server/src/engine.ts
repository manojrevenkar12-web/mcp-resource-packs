/**
 * The portfolio engine: a structured query over a workspace, read through a resource pack.
 * A port of src/resourcepacks/engine.py; test/conformance.test.ts holds both to the same answers.
 */
import type { Answer, Pack, Query, Rules, Template, Where, Workspace } from "./types.js";

export type Task = {
  project: string;
  name: unknown;
  status: string | undefined;
  progress: number;
  start: string | null; // ISO day
  due: string | null;
  owner: unknown;
  done: boolean;
  milestone: boolean;
};

const DAY = 86_400_000;
const days = (iso: string) => Date.UTC(+iso.slice(0, 4), +iso.slice(5, 7) - 1, +iso.slice(8, 10)) / DAY;

export function parseDate(v: unknown, fmt: Template["dates"]): string | null {
  if (v === null || v === undefined || v === "") return null;
  if (fmt === "dmy_text") {
    const m = /^(\d{1,2})\.(\d{1,2})\.(\d{4})$/.exec(String(v).trim());
    return m ? `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}` : null;
  }
  const s = String(v).slice(0, 10);
  return /^\d{4}-\d{2}-\d{2}$/.test(s) ? s : null;
}

export function parseProgress(v: unknown, fmt: Template["progress"]): number {
  if (v === null || v === undefined || v === "") return 0;
  if (fmt === "percent_text") {
    const m = /(\d+(?:[.,]\d+)?)/.exec(String(v));
    return m ? Number(m[1].replace(",", ".")) / 100 : 0;
  }
  const x = Number(v);
  return fmt === "percent" ? x / 100 : x;
}

export function fiscalQuarter(iso: string, startMonth: number): [number, number] {
  const year = +iso.slice(0, 4);
  const month = +iso.slice(5, 7);
  const shifted = (((month - startMonth) % 12) + 12) % 12;
  const fy = year + (month >= startMonth && startMonth !== 1 ? 1 : 0);
  return [fy, Math.floor(shifted / 3) + 1];
}

export function tasks(ws: Workspace, pack: Pack): Task[] {
  const rules = pack.rules;
  const out: Task[] = [];
  for (const s of ws.sheets) {
    const meta = pack.sheets[String(s.id)];
    if (!meta || meta.kind !== "project" || !meta.template) continue;
    const t = pack.templates[meta.template];
    if (!t) continue;
    const title = new Map(s.columns.map((c) => [c.id, c.title]));
    const roleOf = new Map(Object.entries(t.roles).map(([role, col]) => [col as string, role]));
    const parents = new Set(s.rows.map((r) => r.parentId).filter((x): x is number => !!x));
    for (const r of s.rows) {
      if (parents.has(r.id) && (rules.summary_rows ?? "exclude") === "exclude") continue;
      const v: Record<string, unknown> = {};
      for (const cell of r.cells) {
        const role = roleOf.get(title.get(cell.columnId) ?? "");
        if (role) v[role] = cell.value;
      }
      const start = parseDate(v.start, t.dates);
      const due = parseDate(v.due, t.dates);
      const progress = parseProgress(v.progress, t.progress);
      const done = rules.done === "checkbox" && "done" in t.roles ? Boolean(v.done) : progress >= 0.999;
      const milestone = rules.milestone === "flag" && "milestone" in t.roles ? Boolean(v.milestone) : start !== null && start === due;
      out.push({
        project: s.name,
        name: v.task ?? null,
        status: t.status_values[String(v.status)],
        progress,
        start,
        due,
        owner: v.owner ?? null,
        done,
        milestone,
      });
    }
  }
  return out;
}

export function atRisk(x: Task, rules: Rules, today: string): boolean {
  if (x.done) return false;
  if (x.status === "at_risk" || x.status === "off_track") return true;
  const rule = rules.at_risk;
  if (rule.kind === "status_or_due_soon" && x.due !== null) {
    const d = days(x.due) - days(today);
    return d >= 0 && d <= rule.days && x.progress < rule.below;
  }
  return false;
}

function match(x: Task, where: Where, rules: Rules, today: string): boolean {
  for (const [k, v] of Object.entries(where)) {
    if (k === "project" && x.project !== v) return false;
    if (k === "owner" && x.owner !== v) return false;
    if (k === "done" && x.done !== v) return false;
    if (k === "overdue" && (!x.done && x.due !== null && days(x.due) < days(today)) !== v) return false;
    if (k === "at_risk" && atRisk(x, rules, today) !== v) return false;
    if (k === "due_within_days" && !(x.due !== null && days(x.due) >= days(today) && days(x.due) <= days(today) + (v as number))) return false;
    if (k === "fiscal_quarter") {
      const fq = fiscalQuarter(today, rules.fiscal_start_month);
      if (x.due === null) return false;
      const q = fiscalQuarter(x.due, rules.fiscal_start_month);
      if (q[0] !== fq[0] || q[1] !== fq[1]) return false;
    }
  }
  return true;
}

const byCodePoint = (a: string, b: string) => (a < b ? -1 : a > b ? 1 : 0);

export function run(rows: Task[], q: Query, rules: Rules, today: string): Answer {
  const where = q.where ?? {};
  if (q.entity === "projects") {
    const { at_risk: wantRisk, ...rest } = where;
    const by = new Map<string, Task[]>();
    for (const x of rows) if (match(x, rest, rules, today)) by.set(x.project, [...(by.get(x.project) ?? []), x]);
    const hit: string[] = [];
    for (const [name, xs] of by) {
      if (wantRisk !== undefined) {
        const open = xs.filter((x) => !x.done);
        const share = open.length ? open.filter((x) => atRisk(x, rules, today)).length / open.length : 0;
        if ((share >= (rules.project_at_risk_share ?? 0.2)) !== wantRisk) continue;
      }
      hit.push(name);
    }
    hit.sort(byCodePoint);
    return q.op === "list" ? hit : hit.length;
  }
  const pool = rows.filter((x) => (q.entity === "milestones" ? x.milestone : true));
  const sel = pool.filter((x) => match(x, where, rules, today));
  switch (q.op) {
    case "count":
      return sel.length;
    case "list":
      return sel.map((x) => `${x.project} / ${String(x.name)}`).sort(byCodePoint);
    case "avg_progress":
      return sel.length ? Math.round((1000 * sel.reduce((a, x) => a + x.progress, 0)) / sel.length) / 10 : null;
    case "top_owner": {
      const counts = new Map<string, number>();
      for (const x of sel) if (x.owner) counts.set(String(x.owner), (counts.get(String(x.owner)) ?? 0) + 1);
      if (!counts.size) return [];
      const best = Math.max(...counts.values());
      return [...counts].filter(([, n]) => n === best).map(([o]) => o).sort(byCodePoint);
    }
  }
}

export const answer = (ws: Workspace, pack: Pack, q: Query, today: string): Answer => run(tasks(ws, pack), q, pack.rules, today);
