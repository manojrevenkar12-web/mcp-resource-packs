import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { firstCustomer, motion as m } from "../../app/theme";
import type { Run } from "../../shared/types";
import { Empty } from "../../shared/ui";

const SOURCE = { inferred: "from the sheets", admin: "confirmed by the admin", workshop: "from the workshop" } as const;

export function Translate({ run }: { run: Run }) {
  const start = run.customers.find((c) => c.id === firstCustomer) ?? run.customers[0];
  const [id, setId] = useState(start.id);
  const c = run.customers.find((x) => x.id === id) ?? start;
  return (
    <div className="translate">
      <div className="chips" role="group" aria-label="Customer">
        {run.customers.map((x) => (
          <button key={x.id} className="chip" aria-pressed={x.id === c.id} onClick={() => setId(x.id)} title={x.name}>
            {x.id}
          </button>
        ))}
      </div>
      <p className="who">
        <b>{c.name}</b> <span className="muted">
          {c.industry}, {c.lang === "de" ? "German" : c.lang === "fr" ? "French" : "English"}, {c.sheets} sheets, {c.templates > 1 ? "two templates" : "one template"}
          {c.regulated ? ", regulated" : ""}
        </span>
      </p>
      {c.translations.length ? (
        <div className="sheet" role="table" aria-label={`What ${c.name}'s sheets mean`}>
          <div className="sheet-head" role="row">
            <span role="columnheader">In their sheets</span>
            <span aria-hidden="true" />
            <span role="columnheader">Means</span>
            <span role="columnheader">Source</span>
          </div>
          <AnimatePresence mode="wait" initial={false}>
            <motion.div key={c.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={m.swap}>
              {c.translations.map((t, i) => (
                <motion.div
                  key={`${t.seen}-${t.means}`}
                  role="row"
                  className={`sheet-row src-${t.source}`}
                  initial={{ opacity: 0, x: -6 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ ...m.row, delay: i * m.stagger }}
                >
                  <span role="cell" className="seen">{t.seen}</span>
                  <span aria-hidden="true" className="arrow">→</span>
                  <span role="cell">{t.means}</span>
                  <span role="cell" className="source">{SOURCE[t.source]}</span>
                </motion.div>
              ))}
            </motion.div>
          </AnimatePresence>
        </div>
      ) : (
        <Empty>Nothing to translate for this customer: every column and value used the usual words.</Empty>
      )}
    </div>
  );
}
