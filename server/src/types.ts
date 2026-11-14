/** The Smartsheet API's shape for a sheet, and the resource pack that says what it means. */

export type Cell = { columnId: number; value: unknown };
export type Row = { id: number; parentId?: number | null; cells: Cell[] };
export type Column = { id: number; title: string; type: string; primary?: boolean; options?: string[]; symbol?: string };
export type Sheet = { id: number; name: string; columns: Column[]; rows: Row[] };
export type Workspace = { customer: string; name?: string; sheets: Sheet[] };

export type Canon = "on_track" | "at_risk" | "off_track";
export type Template = {
  roles: Partial<Record<"task" | "status" | "progress" | "start" | "due" | "owner" | "done" | "milestone", string>>;
  status_values: Record<string, Canon>;
  progress: "fraction" | "percent" | "percent_text";
  dates: "iso" | "dmy_text";
};
export type Rules = {
  at_risk: { kind: "status" } | { kind: "status_or_due_soon"; days: number; below: number };
  fiscal_start_month: number;
  done: "progress" | "checkbox";
  milestone: "flag" | "zero_duration";
  summary_rows?: "exclude" | "include";
  project_at_risk_share?: number;
};
export type Pack = {
  customer: string;
  sheets: Record<string, { kind: "project" | "archive" | "other" | string; template: string | null }>;
  templates: Record<string, Template>;
  rules: Rules;
  glossary: Record<string, string>;
  workflow?: { regulated: boolean; tolerance: number };
};

export type Where = {
  project?: string;
  owner?: string;
  overdue?: boolean;
  at_risk?: boolean;
  done?: boolean;
  due_within_days?: number;
  fiscal_quarter?: "current";
};
export type Query = { op: "count" | "list" | "avg_progress" | "top_owner"; entity: "tasks" | "milestones" | "projects"; where?: Where };
export type Answer = number | string[] | null;
