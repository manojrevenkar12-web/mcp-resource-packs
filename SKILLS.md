# SKILLS.md

Repeatable tasks in this repository and how to do each.

## Onboard a new customer

1. Snapshot their workspace (or point `SmartsheetSource` at it) and run `infer.draft` on it.
2. Take the review queue (`review.queue`) to their admin; record answers with `review.apply_admin`.
3. Run the workshop from the generated WORKSHOP.md; record with `review.apply_workshop`.
4. Build the kit with `kits.build`, run `kits.lint`, and fix what it reports. Ship `pack.json` with the server.

## Add a convention the field keeps seeing

1. Check the field findings table in README.md (from `findings` in the report).
2. Add the title or value to `src/resourcepacks/lexicon.py` with the role the admins gave it.
3. Run the evaluation: review questions per customer should fall and nothing confident should turn wrong
   (`tests/test_infer.py` checks that every confident decision is right).

## Add a query the assistant can ask

1. Add the filter or op to `engine.py` and `server/src/engine.ts`, and to the zod schema in `server/src/server.ts`.
2. Add it to the queries in `scripts/export.py`, regenerate the fixture, and run both test suites.

## Add a coordination pattern

1. Add it to `patterns.simulate` and `config/packs.toml` `[patterns].order`, with the rule in `patterns.choose`.
2. The report's pattern table and `tests/test_kits.py` show what it costs and what it writes wrong.
