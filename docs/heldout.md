# Held-out run

Run once on 14 November 2026 with the code and settings the dev world ended on (`config/heldout.lock`, commit
4898ce7). The held-out world has 14 other customers (244 sheets, 14,941 rows, 840 questions), a French-speaking
third, status picklists in emoji and in words the base vocabulary had never seen (Vert / Orange / Rouge, Healthy /
Concern / Escalated), progress typed as "45 %", older templates with dates typed as text, and archives named only by a
year. The numbers below are from that one run; nothing was tuned on it.

## What held

- **The kit against raw sheets:** 789 of 840 questions right (93.9%) against 298 (35.5%), with 558 tokens per
  question against 36,797. 13 of 14 customers passed acceptance; none did when the assistant read raw sheets.
- **Review found what it did not know.** 61 questions for admins across 14 customers (4.4 each, against 2.3 on dev),
  most of them French titles and status words. Those are now the top rows of the field findings table: Vert, Orange,
  Rouge, Statut, % Achevé.
- **The lint did its job.** The one customer whose kit failed acceptance (C01) was marked not ready, so the kit
  would not have been handed to a consultant.

## What went wrong

### A done box nobody asked about (C01: 25 of 60 right)

C01 is a French customer with two templates, progress typed as "45 %" and tasks signed off with a tick box called
"Terminé". The workshop said a task is done when that box is ticked. But the draft had never assigned the box a role:

- the value check for an unnamed tick box ("are ticked rows nearly complete?") only read progress stored as a number,
  so with "45 %" it saw nothing;
- and a column that got no role produced no review item, so the admin was never asked about it.

The engine then fell back to "done means 100%", which this customer does not use, and 35 answers were wrong.

**Changed on dev afterwards:**

- The tick-box check reads progress in the column's own format (0.7, 70 and "70 %" are the same).
- Every tick box, picklist, contact or date column with no role becomes a question for the admin ("what does the
  column "Drapeau" hold?").
- The lint fails a kit whose workshop rule needs a column no live template has ("done means a ticked box, but no
  template has a done column").
- `tests/test_infer.py` and `tests/test_kits.py` cover all three; the dev world now has progress typed as text too.

### Agents wrote wrong status lines with a pack that was wrong

The maker + checker pattern wrote 34 wrong lines, all at C01: the checker recomputes every number with the engine
and the customer's pack, so when the pack is wrong, the checker agrees with the wrong number. A person approving each
line caught 30 of them.

**Changed on dev afterwards:** agents write status lines only for customers whose kit passes the lint
(`switched_on` in the report). C01's lines would have been held back.

### Archives named only by a year (4 confident wrong decisions)

"Fleet Refit 2024"-style archives had no archive word in their name and recent enough dates, so the draft called
four of them live projects with 0.9 confidence. Confident wrong decisions are the ones review never sees; on dev there
had been none.

**Changed on dev afterwards:** a sheet where every row is 100% complete is proposed as an archive with low
confidence, so the admin is asked. The dev world now has year-named archives; it reproduced the problem (2 confident
wrong decisions) and has none after the change.

## Not changed

The gate in `config/gate.toml` stayed where it was set before the run. The held-out numbers in the README are the
ones above; the fixes are measured on the dev world only.
