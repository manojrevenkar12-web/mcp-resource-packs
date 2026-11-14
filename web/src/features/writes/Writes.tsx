import type { Run } from "../../shared/types";
import { Empty, Section } from "../../shared/ui";

const KIND = { role: "column", status_value: "status value", sheet_kind: "sheet" } as Record<string, string>;

export function Writes({ run, patterns }: { run: Run; patterns: Record<string, string> }) {
  const t = run.patterns.totals;
  const chosen = run.patterns.per_customer.reduce<Record<string, number>>((a, r) => ({ ...a, [r.chosen]: (a[r.chosen] ?? 0) + 1 }), {});
  const proposals = run.findings.proposals;
  return (
    <div className="pair">
      <Section id="writes" title="Weekly status lines" lede="Each pattern wrote the same lines; the chosen one is picked per customer from the workshop and a pilot.">
        <table className="plain-table">
          <thead>
            <tr>
              <th scope="col">Pattern</th>
              <th scope="col" className="num">Lines</th>
              <th scope="col" className="num">Wrong</th>
              <th scope="col" className="num">Person min</th>
              <th scope="col" className="num">Customers</th>
            </tr>
          </thead>
          <tbody>
            {[...Object.keys(patterns), "chosen"].map((k) => (
              <tr key={k} className={k === "chosen" ? "total" : undefined}>
                <th scope="row">{k === "chosen" ? "Chosen per customer" : patterns[k]}</th>
                <td className="num">{t[k].lines}</td>
                <td className={`num ${t[k].wrong ? "bad" : ""}`}>{t[k].wrong}</td>
                <td className="num">{Math.round(t[k].person_minutes)}</td>
                <td className="num">{k === "chosen" ? run.patterns.per_customer.length : (chosen[k] ?? 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="note">
          {run.kits.ready} of {run.kits.total} Deployment Kits pass their lint. A kit built from the draft alone fails it on average with{" "}
          {(Object.values(run.kits.per_customer).reduce((a, k) => a + k.draft_problems, 0) / run.kits.total).toFixed(1)} problems.
        </p>
      </Section>
      <Section id="findings" title="Field findings for the platform" lede="Seen at two or more customers and confirmed by their admins: proposed for the base vocabulary.">
        {proposals.length ? (
          <ul className="findings">
            {proposals.map((p) => (
              <li key={`${p.kind}-${p.key}`}>
                <span className="col-chip">{p.key}</span>
                <span>
                  {KIND[p.kind] ?? p.kind} meaning <b>{p.answer.replace("_", " ")}</b>
                </span>
                <span className="muted small">{p.customers.length} customers</span>
              </li>
            ))}
          </ul>
        ) : (
          <Empty>No title or value was unclear at more than one customer.</Empty>
        )}
      </Section>
    </div>
  );
}
