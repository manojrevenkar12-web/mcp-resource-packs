/** The pack in words an assistant (and a person) can read: what each column means and what the rules are. */
import type { Pack } from "./types.js";

const ROLE = {
  task: "task name",
  status: "traffic-light status",
  progress: "completion",
  start: "start date",
  due: "due date",
  owner: "assignee",
  done: "signed-off tick box",
  milestone: "milestone tick box",
} as const;
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

export function rulesText(p: Pack): string {
  const r = p.rules;
  const risk =
    r.at_risk.kind === "status"
      ? "A task is at risk when its status is at risk or off track."
      : `A task is at risk when its status is at risk or off track, or when it is due within ${r.at_risk.days} days and under ${Math.round(r.at_risk.below * 100)}% complete.`;
  return [
    `# Rules for ${p.customer}`,
    "",
    `- ${risk}`,
    `- A project is at risk when at least ${Math.round((r.project_at_risk_share ?? 0.2) * 100)}% of its open tasks are at risk.`,
    `- A task is done ${r.done === "checkbox" ? "when its done box is ticked (not when it shows 100%)" : "when it is 100% complete"}.`,
    `- Milestones are ${r.milestone === "flag" ? "rows with the milestone box ticked" : "rows that start and end on the same day"}.`,
    `- The financial year starts in ${MONTHS[r.fiscal_start_month - 1]}; "this quarter" means the fiscal quarter.`,
    `- Phase rows that group tasks are ${r.summary_rows === "include" ? "counted" : "not counted"} as tasks.`,
    "- Archived projects and sheets that are not project plans are left out.",
    "",
    "Answer counts, lists and averages with the portfolio_query tool rather than by reading rows.",
  ].join("\n");
}

export function glossaryText(p: Pack): string {
  const lines = Object.entries(p.glossary).map(([k, v]) => `- "${k}" means ${v.replace("_", " ")}`);
  return [`# Words ${p.customer} uses`, "", ...(lines.length ? lines : ["- none beyond the usual ones"])].join("\n");
}

export function semantics(p: Pack, sheetNames: Map<string, string>): object {
  const sheets = Object.entries(p.sheets).map(([id, m]) => ({ sheet: sheetNames.get(id) ?? id, kind: m.kind, template: m.template }));
  const templates = Object.fromEntries(
    Object.entries(p.templates).map(([sig, t]) => [
      sig,
      {
        columns: Object.fromEntries(Object.entries(t.roles).map(([role, col]) => [col as string, ROLE[role as keyof typeof ROLE]])),
        status_values: t.status_values,
        progress: t.progress,
        dates: t.dates,
      },
    ]),
  );
  return { customer: p.customer, sheets, templates };
}
