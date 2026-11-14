import { order } from "../../app/theme";
import type { Run } from "../../shared/types";

export function Matrix({ run, names }: { run: Run; names: Record<string, string> }) {
  const cols = order.filter((k) => run.designs[k]);
  return (
    <div className="matrix-wrap">
      <table className="matrix">
        <thead>
          <tr>
            <th scope="col">Customer</th>
            {cols.map((k) => (
              <th scope="col" key={k}>
                {names[k]}
              </th>
            ))}
            <th scope="col">Admin questions</th>
            <th scope="col">Kit</th>
          </tr>
        </thead>
        <tbody>
          {run.customers.map((c) => (
            <tr key={c.id}>
              <th scope="row">
                {c.id} <span className="muted">{c.name}</span>
              </th>
              {cols.map((k) => {
                const d = c.designs[k];
                return (
                  <td key={k} className={d.accepted ? "pass" : "fail"} aria-label={`${d.right} of ${d.questions} right, ${d.accepted ? "accepted" : "not accepted"}`}>
                    {d.right}
                    <span className="of">/{d.questions}</span>
                  </td>
                );
              })}
              <td className="plain">{c.review_items}</td>
              <td className="plain">{c.kit_ready ? "ready" : "not done"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
