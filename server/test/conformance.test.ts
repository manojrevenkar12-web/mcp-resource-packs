import { describe, expect, it } from "vitest";
import { answer } from "../src/engine.js";
import type { Answer, Pack, Query, Workspace } from "../src/types.js";
import fixture from "./fixtures/conformance.json";

type Case = { variant: string; query: Query; answer: Answer };
const f = fixture as unknown as { today: string; workspaces: Record<string, Workspace>; packs: Record<string, Pack>; cases: Case[] };
const ws = (variant: string) => f.workspaces[variant.split(":")[0]];

const same = (a: Answer, b: Answer) =>
  typeof a === "number" && typeof b === "number" && !Number.isInteger(b) ? Math.abs(a - b) <= 0.06 : JSON.stringify(a) === JSON.stringify(b);

describe("the TypeScript engine answers as the Python engine does", () => {
  it(`agrees on all ${f.cases.length} cases across ${Object.keys(f.packs).length} rule variants`, () => {
    const wrong = f.cases.filter((c) => !same(answer(ws(c.variant), f.packs[c.variant], c.query, f.today), c.answer));
    expect(wrong.map((c) => ({ ...c, got: answer(ws(c.variant), f.packs[c.variant], c.query, f.today) })).slice(0, 3)).toEqual([]);
  });

  it("the rule variants change answers, so the cases test the rules", () => {
    const byVariant = (v: string) => f.cases.filter((c) => c.variant === v).map((c) => JSON.stringify(c.answer));
    for (const v of Object.keys(f.packs).filter((v) => !v.endsWith(":signed_off"))) {
      expect(byVariant(v), v).not.toEqual(byVariant(`${v.split(":")[0]}:signed_off`));
    }
  });
});
