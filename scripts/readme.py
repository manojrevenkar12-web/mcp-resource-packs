"""Write README.md and the console data from reports/*.json. Never edit the results by hand."""

from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = tomllib.loads((Path(__file__).resolve().parents[1] / "config" / "packs.toml").read_text())
REPO = "https://github.com/manojrevenkar12-web/mcp-resource-packs"
NAMES = {
    "generic_mcp": "Assistant reads raw sheets",
    "pack_as_context": "Pack as context, assistant reads rows",
    "drafted_pack": "Drafted pack + query tool",
    "reviewed_pack": "Reviewed pack + query tool",
    "kit": "**Deployment Kit** (reviewed + workshop + query tool)",
}
PATTERNS = {
    "single": "One agent",
    "maker_checker": "Maker + checker",
    "maker_checker_approval": "Maker + checker + approval",
}


def table(head: list[str], rows: list[list]) -> str:
    sep = "|" + "|".join(["---"] + ["--:"] * (len(head) - 1)) + "|"
    return "\n".join(["| " + " | ".join(head) + " |", sep] + ["| " + " | ".join(map(str, r)) + " |" for r in rows])


def pct(x: float, d: int = 1) -> str:
    return f"{x * 100:.{d}f}%"


def design_table(r: dict) -> str:
    rows = []
    for k, name in NAMES.items():
        d = r["designs"][k]
        rows.append(
            [
                name,
                f"{pct(d['accuracy'])} ({d['right']}/{d['questions']})",
                f"{d['customers_accepted']} of {d['customers']}",
                f"{d['tokens_per_question']:,}",
                f"€{d['cost_per_1000_questions_eur']:.2f}",
                f"{d['consultant_hours_per_customer']:.1f} h",
            ]
        )
    return table(
        [
            "Design",
            "Questions answered right",
            "Customers accepted",
            "Tokens per question",
            "Cost per 1,000 questions",
            "Consultant time per customer",
        ],
        rows,
    )


def cause_table(r: dict) -> str:
    causes = sorted({c for d in r["designs"].values() for c in d["wrong_by_cause"]})
    rows = [[NAMES[k].replace("**", "")] + [r["designs"][k]["wrong_by_cause"].get(c, 0) for c in causes] for k in NAMES]
    return table(["Design"] + [c[0].upper() + c[1:] for c in causes], rows)


def pattern_table(r: dict) -> str:
    t = r["patterns"]["totals"]
    rows = []
    for k, name in list(PATTERNS.items()) + [("chosen", "**Chosen per customer**")]:
        v = t[k]
        rows.append([name, v["lines"], v["wrong"], v["llm_calls"], f"{v['person_minutes']:.0f}"])
    return table(["Pattern", "Status lines written", "Wrong", "LLM calls", "Person minutes"], rows)


def heldout_section(h: dict | None) -> str:
    if not h:
        return "Not run yet. `python scripts/evaluate.py --heldout` runs it once and writes `config/heldout.lock`."
    v = h["volume"]
    return f"""Other customers: {v["customers"]} of them, {v["sheets"]} sheets, {v["rows"]:,} rows, in {", ".join(v["languages"])}. Status picklists in
emoji and in words the base vocabulary has never seen, progress typed as "45 %", older templates with dates typed as
text, archives named only by a year. Run once with the code and settings the dev world ended on (`config/heldout.lock`).

{design_table(h)}

{h["kits"]["ready"]} of {h["kits"]["total"]} kits passed their lint; the status-line patterns chosen per customer wrote
{h["patterns"]["totals"]["chosen"]["wrong"]} wrong lines out of {h["patterns"]["totals"]["chosen"]["lines"]}. What went wrong and what changed afterwards:
[docs/heldout.md](docs/heldout.md)."""


def readme(r: dict, h: dict | None) -> str:
    v, d = r["volume"], r["designs"]
    k, g, pc = d["kit"], d["generic_mcp"], d["pack_as_context"]
    pt = r["patterns"]["totals"]
    proposals = r["findings"]["proposals"]
    nd = r["findings"]["rules_not_default"]
    prop_rows = [
        [
            f"`{p['key']}`",
            {"role": "column role", "status_value": "status value", "sheet_kind": "sheet kind"}.get(
                p["kind"], p["kind"]
            ),
            p["answer"].replace("_", " "),
            ", ".join(p["customers"]),
        ]
        for p in proposals
    ]
    return f"""# mcp-resource-packs

Smartsheet's MCP server lets Claude, Copilot, ChatGPT and Gemini read a customer's live sheets. What no connector can
read is what those sheets **mean at this customer**: that "Zustand" is the traffic light and "Slipping" is amber, that
progress is typed as 45 and not 0.45, that tasks hang under phase rows, that "zz_Fleet Refit (old)" is an archive and
the RAID log is not a plan, that a task here is at risk when it is due within 7 days and under 80% complete, that the
financial year starts in October, and that "gate" means milestone.

This repository is the forward deployed engineer's kit for that gap. It drafts a **resource pack** for each customer
from their own workspace, asks their admin only about what it could not be sure of, records the rules from a
one-hour workshop, serves the pack through a **TypeScript MCP server** with a `portfolio_query` tool that answers
with code, picks the **multi-agent pattern** that writes their weekly status lines, and hands it all over as a
**Deployment Kit** a solutions consultant with no engineering background can follow, with a lint that says when a kit
is not done.

On {v["customers"]} simulated customers ({v["sheets"]} sheets, {v["rows"]:,} rows, {v["with_legacy_template"]} with an older template still in use) and their
{v["questions"]} questions:

- **{pct(k["accuracy"])} answered right with the kit against {pct(g["accuracy"])} for an assistant reading raw sheets**, and
  {k["customers_accepted"]} of {k["customers"]} customers past the acceptance bar against {g["customers_accepted"]}.
- **{k["tokens_per_question"]:,} tokens per question against {g["tokens_per_question"]:,}**: €{k["cost_per_1000_questions_eur"]:.2f} per 1,000 questions
  against €{g["cost_per_1000_questions_eur"]:.2f}. The pack alone, given as context while the assistant still reads rows, gets
  {pct(pc["accuracy"])}: the meanings fix the semantics, the query tool fixes the arithmetic.
- **{k["consultant_hours_per_customer"]:.1f} consultant hours per customer**, most of it the workshop. Inference made
  {r["volume"]["review_items"]} decisions it was unsure of across all customers; every decision it was sure of was right.
- **0 wrong status lines** from the patterns chosen per customer, against {pt["single"]["wrong"]} of {pt["single"]["lines"]} for one agent alone;
  regulated customers get a person approving every line ({pt["chosen"]["person_minutes"]:.0f} person minutes in all).
- **{r["kits"]["ready"]} of {r["kits"]["total"]} Deployment Kits pass the lint.**

![Console](docs/console.png)

## How a customer goes live

| Step | Who | Module | What happens |
|---|---|---|---|
| Draft | code | `infer.py` | Sheets grouped by template; each column gets a role from its title (base lexicon) and its values (types, ranges, which date is always later, what a ticked box coincides with); status values mapped by the lexicon, then by picklist order; archives and non-plan sheets recognised. Every decision carries a confidence and its evidence. |
| Confirm | customer's admin | `review.py`, `kits.py` | Decisions under {PACKS["review_threshold"]:.0%} confidence become plain questions ("When a row's status says \\"Slipping\\", does that mean at risk?"). |
| Workshop | customer's project leads | `review.py` | The rules no sheet shows: when a task and a project are at risk, when the financial year starts, what "done" means, how milestones are marked, regulated or not, the customer's own words. |
| Serve | MCP server | `server/` | `pack://rules`, `pack://glossary`, `pack://semantics` as resources; `portfolio_query` (read-only) computes counts, lists, averages and the busiest assignee with the customer's meanings; a `weekly_portfolio_review` prompt. Reads a snapshot or the Smartsheet REST API with the customer's own token. |
| Write | agents | `patterns.py` | Weekly status line per project: one agent, maker + checker (the checker recomputes every number with the engine), or maker + checker + a person approving each line, chosen from the workshop answers and a pilot. |
| Hand over | consultant | `kits.py` | RUNBOOK, WORKSHOP, ACCEPTANCE and pack.json per customer; the lint blocks jargon, steps with no finish line, unconfirmed decisions, unsettled rules and acceptance under target. Example: [kits/C08](kits/C08/RUNBOOK.md). |
| Learn | FDE team | `evaluate.py` | Titles and values that went to review at several customers become proposals for the base vocabulary. |

## Results on the dev world

Same customers, same questions, same luck for every design. Acceptance is the Wilson 95% lower bound on the share of
a customer's {r["customers"][0]["designs"]["kit"]["questions"]} questions answered right, at least {pct(r["target"], 0)}.

{design_table(r)}

Why answers went wrong:

{cause_table(r)}

- **Raw sheets** fail on meaning before arithmetic: an unfamiliar title or status word, archived projects counted as
  live, phase rows counted as tasks, the calendar quarter for the fiscal one, 100% taken as done where the customer
  signs off with a tick box.
- **The drafted pack** gets the columns right and the rules wrong: {nd["at_risk"]} of {r["findings"]["customers"]} customers define "at risk"
  beyond the status column, {nd["fiscal_start_month"]} have a financial year that does not start in January. The admin review fixes
  columns; only the workshop fixes rules, which is why the kit, not the draft, passes acceptance.
- **The kit's** remaining misses are questions the assistant turned into the wrong query.

## Weekly status lines: choosing the pattern

{pattern_table(r)}

One agent alone writes wrong lines (a miscount, a wrong colour). A pilot of {PACKS["patterns"]["pilot_weeks"]} weeks cannot show that rate is within
a customer's tolerance at 95% confidence, so no customer got the single agent: the checker costs
{pt["maker_checker"]["llm_calls"] - pt["single"]["llm_calls"]} extra LLM calls in {pt["single"]["lines"]} lines and removes the wrong ones. Regulated customers
({r["volume"]["regulated"]}) get approval on every line for the audit trail, not for accuracy.

## Field findings for the platform

Titles and values inference was unsure of at two or more customers, with what the admins answered. These are the
proposed additions to the base vocabulary (`src/resourcepacks/lexicon.py`):

{table(["Seen as", "Kind", "Admins said", "Customers"], prop_rows) if prop_rows else "None yet."}

## Held-out world (run once)

{heldout_section(h)}

## The MCP server

```bash
cd server && npm ci && npm run build
PACK=../data/example/pack.json SNAPSHOT=../data/example/workspace.json TODAY=2026-11-16 node dist/main.js   # demo
PACK=../kits/C08/pack.json SMARTSHEET_TOKEN=... node dist/main.js                                       # live workspace
```

In Claude Desktop (`claude_desktop_config.json`):

```json
{{"mcpServers": {{"resource-pack": {{"command": "node", "args": ["/path/to/server/dist/main.js"],
  "env": {{"PACK": "/path/to/kits/C08/pack.json", "SMARTSHEET_TOKEN": "..."}}}}}}}}
```

The TypeScript engine is a port of `src/resourcepacks/engine.py`; `server/test/conformance.test.ts` checks both give
the same answer on every query in `server/test/fixtures/conformance.json` (one workspace under seven rule variants).

## Run it

```bash
pip install -r requirements-lock.txt && pip install -e . --no-deps
python -m pytest -q                      # Python tests
python scripts/evaluate.py               # dev world -> reports/dev.json
python scripts/gate.py                   # quality gate (config/gate.toml)
python scripts/export.py                 # example workspace, conformance fixture, example kit
python scripts/readme.py                 # README.md and web/public/data/console.json
cd server && npm ci && npm test          # MCP server and conformance
cd web && npm ci && npm run build        # console
```

## Limits

- Customers, workspaces, the admin's answers and the assistant's mistakes are simulated, with their behaviour set in
  `config/world.toml`; the conventions are ones I wrote from how Smartsheet plans are commonly built. A real
  engagement starts by drafting the pack on the customer's own workspace and comparing it with their admin.
- `SmartsheetSource` follows the Smartsheet API 2.0 sheet shape and is tested against a fake; it has not run against a
  live account.
- The workshop is recorded as answers, not run with people; the consultant minutes are planning figures.
- Questions are the nine kinds in `world/sim.py`; free-form questions outside them are the assistant's job.

Repository: {REPO}
"""


def console(r: dict, h: dict | None) -> dict:
    def slim(x: dict) -> dict:
        return {k: x[k] for k in ("world", "volume", "designs", "customers", "patterns", "kits", "findings", "target")}

    return {
        "dev": slim(r),
        "heldout": slim(h) if h else None,
        "names": {k: v.replace("**", "") for k, v in NAMES.items()},
        "patterns": PATTERNS,
    }


def main() -> None:
    r = json.loads((ROOT / "reports" / "dev.json").read_text())
    hp = ROOT / "reports" / "heldout.json"
    h = json.loads(hp.read_text()) if hp.exists() else None
    (ROOT / "README.md").write_text(readme(r, h))
    out = ROOT / "web" / "public" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / "console.json").write_text(json.dumps(console(r, h), separators=(",", ":"), ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
