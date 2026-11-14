import { motion } from "framer-motion";
import { eur, motion as m, num, order, pct, tokenAxis } from "../../app/theme";
import type { Run } from "../../shared/types";

const logShare = (t: number) => Math.min(1, Math.max(0, (Math.log10(Math.max(t, 1)) - tokenAxis.min) / (tokenAxis.max - tokenAxis.min)));

export function Designs({ run, names }: { run: Run; names: Record<string, string> }) {
  return (
    <div className="designs" role="table" aria-label="Designs compared">
      <div className="designs-head" role="row">
        <span role="columnheader">Design</span>
        <span role="columnheader">Answered right</span>
        <span role="columnheader">Accepted</span>
        <span role="columnheader">Tokens per question</span>
      </div>
      {order
        .filter((k) => run.designs[k])
        .map((k, i) => {
          const d = run.designs[k];
          return (
            <div key={k} role="row" className={`design-row ${k === "kit" ? "is-kit" : ""}`}>
              <span role="cell" className="design-name">
                {names[k]}
                <span className="muted small">
                  {eur(d.cost_per_1000_questions_eur)} per 1,000 questions, {d.consultant_hours_per_customer.toFixed(1)} h of consultant time per customer
                </span>
              </span>
              <span role="cell" className="bar-cell" aria-label={`${pct(d.accuracy)} right`}>
                <span className="track">
                  <motion.i className="fill acc" initial={{ width: 0 }} animate={{ width: `${d.accuracy * 100}%` }} transition={{ ...m.bar, delay: i * m.stagger }} />
                </span>
                <b>{pct(d.accuracy)}</b>
              </span>
              <span role="cell" className="accepted">
                <b>{d.customers_accepted}</b> of {d.customers}
              </span>
              <span role="cell" className="bar-cell" aria-label={`${num(d.tokens_per_question)} tokens`}>
                <span className="track">
                  <motion.i className="fill tok" initial={{ width: 0 }} animate={{ width: `${logShare(d.tokens_per_question) * 100}%` }} transition={{ ...m.bar, delay: i * m.stagger }} />
                </span>
                <b>{num(d.tokens_per_question)}</b>
              </span>
            </div>
          );
        })}
      <p className="note">Token bars use a log scale from 100 to 100,000.</p>
    </div>
  );
}
