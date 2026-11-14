export type Design = {
  right: number;
  questions: number;
  accuracy: number;
  customers_accepted: number;
  customers: number;
  tokens_per_question: number;
  cost_per_1000_questions_eur: number;
  latency_s: number;
  consultant_hours_per_customer: number;
  wrong_by_cause: Record<string, number>;
};

export type Translation = { seen: string; means: string; source: "inferred" | "admin" | "workshop"; kind: string };

export type CustomerRow = {
  id: string;
  name: string;
  industry: string;
  lang: string;
  regulated: boolean;
  sheets: number;
  rows: number;
  templates: number;
  review_items: number;
  designs: Record<string, { right: number; questions: number; lower: number; accepted: boolean; tokens_per_question: number }>;
  pattern: string;
  kit_ready: boolean;
  translations: Translation[];
};

export type PatternTotals = { lines: number; wrong: number; llm_calls: number; person_minutes: number; over_tolerance?: number };

export type Run = {
  world: string;
  target: number;
  volume: { customers: number; sheets: number; rows: number; questions: number; languages: string[]; regulated: number; with_legacy_template: number; review_items: number };
  designs: Record<string, Design>;
  customers: CustomerRow[];
  patterns: {
    totals: Record<string, PatternTotals>;
    per_customer: { customer: string; regulated: boolean; tolerance: number; projects: number; chosen: string; why: string }[];
  };
  kits: { ready: number; total: number; per_customer: Record<string, { ready: boolean; problems: string[]; draft_problems: number; questions_for_admin: number }> };
  findings: { proposals: { kind: string; key: string; answer: string; customers: string[] }[]; rules_not_default: Record<string, number>; customers: number };
};

export type Console = { dev: Run; heldout: Run | null; names: Record<string, string>; patterns: Record<string, string> };
