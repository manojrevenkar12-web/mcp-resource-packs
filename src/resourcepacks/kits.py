"""Deployment Kits: everything a solutions consultant with no engineering background needs to take one customer
live, generated from the customer's pack and results, and a lint that says when a kit is not done.

A kit is a folder:

- RUNBOOK.md: the steps, in order, in plain words, with every open question for the customer's admin written as a
  question they can answer.
- WORKSHOP.md: the rules the workshop settled and the customer's own words.
- ACCEPTANCE.md: the customer's questions answered against the agreed target, with the lower bound.
- pack.json: what the MCP server serves for this customer.
"""

from __future__ import annotations

import json
import math
import re

JARGON = [
    "json",
    "regex",
    "endpoint",
    "api token",
    "cli",
    "curl",
    "python",
    "npm",
    "schema",
    "yaml",
    "http",
    "sdk",
    "stdout",
    "localhost",
    "repo",
    "commit",
]
ROLE_WORDS = {
    "task": "the name of the task",
    "status": "the traffic-light status (on track, at risk, off track)",
    "progress": "how complete the task is",
    "start": "the start date",
    "due": "the end or due date",
    "owner": "who the task is assigned to",
    "done": "the tick box that says a task is signed off",
    "milestone": "the tick box that marks a milestone",
}
CANON_WORDS = {"on_track": "on track", "at_risk": "at risk", "off_track": "off track"}


def wilson_lower(k: int, n: int, z: float) -> float:
    if n == 0:
        return 0.0
    p = k / n
    d = 1 + z * z / n
    centre = p + z * z / (2 * n)
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (centre - margin) / d


def question_for(item: dict, sheet_names: dict[str, str]) -> str:
    """A review item as a question the customer's admin can answer without knowing what a pack is."""
    sheet = sheet_names.get(item.get("sheet") or "", "the plans")
    k, v = item["kind"], item["value"]
    if k == "sheet_kind":
        what = {
            "project": "a live project plan",
            "archive": "a finished project kept for reference",
            "other": "not a project plan",
        }
        return f'Is the sheet "{sheet}" {what.get(v, v)}?'
    if k == "role":
        return f'In "{sheet}" and sheets like it, does the column "{item["key"]}" hold {ROLE_WORDS.get(v, v)}?'
    if k == "status_value":
        return f'When a row\'s status says "{item["key"]}", does that mean {CANON_WORDS.get(v, v)}?'
    if k == "progress":
        return f'Is "{item["key"]}" entered as {"a share like 0.45" if v == "fraction" else "a number like 45"}?'
    if k == "dates":
        return f'Are the dates in "{item["key"]}" typed as day.month.year?'
    return f"Please confirm {item['key']}: {v}"


def build(customer: dict, pack: dict, draft: dict, result: dict, pattern: dict, cfg: dict) -> dict[str, str]:
    names = {sid: s["name"] for sid, s in customer["sheet_names"].items()}
    asked = [i for i in draft["items"] if i["kind"] != "rule" and i["confidence"] < cfg["review_threshold"]]
    lines = [
        f"# Deployment Kit: {customer['name']}",
        "",
        "Follow the steps in order. Each step says what to do, who to ask and how you know it is finished.",
        "",
        "## Step 1. Connect the workspace",
        "",
        "Ask the customer's Smartsheet admin to connect their workspace to the MCP server in the AI tool they use",
        '(Claude, Copilot, ChatGPT or Gemini). Finished when the admin can ask the assistant "which projects are',
        'listed?" and gets their project names back.',
        "",
        "## Step 2. Confirm what the draft could not be sure about",
        "",
        f"The draft read {len(pack['sheets'])} sheets and was unsure about {len(asked)} things. Ask the admin each",
        "question below and record the answer in the review screen. Finished when every question has an answer.",
        "",
    ]
    if asked:
        for n, it in enumerate(asked, 1):
            lines.append(f"{n}. {question_for(it, names)}")
    else:
        lines.append("Nothing to confirm: every decision was clear from the sheets.")
    lines += [
        "",
        "## Step 3. Run the workshop",
        "",
        "Book an hour with the people who run the projects. Ask the questions in WORKSHOP.md and record the answers.",
        "Finished when every rule in WORKSHOP.md has an answer.",
        "",
        "## Step 4. Check the answers against the customer's own questions",
        "",
        f"Ask the {result['questions']} questions in ACCEPTANCE.md. Finished when the lower bound is at least",
        f"{cfg['acceptance']['target']:.0%}. Now: {result['right']} of {result['questions']} right, lower bound {result['lower']:.1%}.",
        "",
        "## Step 5. Switch on the weekly status lines",
        "",
        f"Pattern: **{pattern['chosen'].replace('_', ' ')}**. Why: {pattern['why']}.",
        "",
        "## Step 6. Hand over",
        "",
        "Walk the customer's admin through this kit. Finished when they can say which sheets the assistant reads,",
        'what "at risk" means for them, and who to call when an answer looks wrong.',
        "",
    ]
    rules = pack["rules"]
    ar = rules["at_risk"]
    ar_text = (
        "a task is at risk when its status says so"
        if ar["kind"] == "status"
        else f"a task is at risk when its status says so, or when it is due within {ar['days']} days and less than {ar['below']:.0%} complete"
    )
    months = [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    workshop = [
        f"# Workshop record: {customer['name']}",
        "",
        "| Question | Answer |",
        "|---|---|",
        f"| When is a task at risk? | {ar_text} |",
        f"| When is a project at risk? | when at least {rules['project_at_risk_share']:.0%} of its open tasks are at risk |",
        f"| When does your financial year start? | {months[rules['fiscal_start_month'] - 1]} |",
        f"| When is a task done? | {'when the done box is ticked' if rules['done'] == 'checkbox' else 'when it is 100% complete'} |",
        f"| How do you mark a milestone? | {'with the milestone tick box' if rules['milestone'] == 'flag' else 'a task that starts and ends on the same day'} |",
        f"| Is this a regulated business where a person must approve what is written? | {'yes' if pack.get('workflow', {}).get('regulated') else 'no'} |",
        "",
        "Words the customer uses:",
        "",
    ] + (
        [f'- "{k}" means {v.replace("_", " ")}' for k, v in sorted(pack["glossary"].items())]
        or ["- none beyond the usual ones"]
    )
    acceptance = [
        f"# Acceptance: {customer['name']}",
        "",
        f"{result['right']} of {result['questions']} questions answered right; lower bound {result['lower']:.1%} (95%), target {cfg['acceptance']['target']:.0%}.",
        "",
        "| Question | Right |",
        "|---|---|",
    ] + [f"| {q['text']} | {'yes' if ok else 'no'} |" for q, ok in result["detail"]]
    served = {k: v for k, v in pack.items() if k != "items"}
    return {
        "RUNBOOK.md": "\n".join(lines) + "\n",
        "WORKSHOP.md": "\n".join(workshop) + "\n",
        "ACCEPTANCE.md": "\n".join(acceptance) + "\n",
        "pack.json": json.dumps(served, indent=1, ensure_ascii=False, sort_keys=True) + "\n",
    }


def lint(files: dict[str, str], pack: dict, result: dict, cfg: dict) -> list[str]:
    """Reasons the kit is not done. Empty means a consultant can take it to the customer."""
    out = []
    runbook = files.get("RUNBOOK.md", "")
    for word in JARGON:
        if re.search(rf"(?i)\b{re.escape(word)}\b", runbook):
            out.append(f'RUNBOOK.md uses "{word}", which a consultant without engineering background may not know')
    for n in range(1, 7):
        if f"## Step {n}." not in runbook:
            out.append(f"RUNBOOK.md is missing step {n}")
    for step in re.split(r"\n## ", runbook)[1:]:
        if "Finished when" not in step and "Pattern:" not in step:
            out.append(f'step "{step.splitlines()[0]}" does not say when it is finished')
    open_items = [
        i for i in pack.get("items", []) if i["source"] == "inferred" and i["confidence"] < cfg["review_threshold"]
    ]
    if open_items:
        out.append(f"{len(open_items)} decisions are still unconfirmed")
    rules_open = [i["key"] for i in pack.get("items", []) if i["kind"] == "rule" and i["source"] != "workshop"]
    if rules_open:
        out.append("rules not settled in the workshop: " + ", ".join(rules_open))
    if result["lower"] < cfg["acceptance"]["target"]:
        out.append(
            f"acceptance lower bound {result['lower']:.1%} is under the {cfg['acceptance']['target']:.0%} target"
        )
    return out
