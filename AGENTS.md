# AGENTS.md

How to work in this repository, for people and coding agents.

## Fast feedback

```bash
python -m pytest -q                         # ~10 s
ruff check . && ruff format --check .
python scripts/evaluate.py                  # ~30 s, writes reports/dev.json
python scripts/gate.py
cd server && npm test                       # MCP server, conformance with the Python engine
```

After changing anything the reports depend on: `python scripts/evaluate.py && python scripts/export.py && python scripts/readme.py`,
then commit the regenerated files. CI fails when a generated file does not match its source.

## Invariants

1. **Nothing that serves reads the truth.** `src/resourcepacks/world/` holds the customers, the truth pack, the
   admin's answers and the assistant's mistakes. Only `scripts/evaluate.py`, `scripts/export.py` and the tests import
   it. `engine.py`, `infer.py`, `review.py`, `kits.py`, `patterns.py` and everything in `server/` never do.
2. **The world does not read the packs' settings.** `config/world.toml` and `config/heldout.toml` drive the world;
   `config/packs.toml` drives inference, review, acceptance and patterns.
3. **Same luck for every design.** Every random draw in the world is keyed by what it is about (customer, question,
   project, week), never by which design asks, so designs differ only by what they do.
4. **The model reads, code decides.** The assistant turns a question into a query; `portfolio_query` computes the
   answer. A drafted status line is written only if the checker's numbers agree.
5. **One engine, two languages.** `engine.py` and `server/src/engine.ts` give the same answers on every case in
   `server/test/fixtures/conformance.json`; change both or neither.
6. **A kit is done when its lint is empty.** `kits.lint` is the definition; do not ship a kit around it.
7. **Settings in config, results generated.** No number in README.md or the console is typed by hand.

## Held-out rule

`python scripts/evaluate.py --heldout` runs the held-out world once and writes `config/heldout.lock`. After that,
changes are measured on the dev world only; findings go in `docs/heldout.md`. The gate in `config/gate.toml` is not
moved after the held-out run.
