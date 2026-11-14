import { AnimatePresence, motion } from "framer-motion";
import { useState } from "react";
import { Matrix } from "../features/customers/Matrix";
import { Designs } from "../features/designs/Designs";
import { Translate } from "../features/translate/Translate";
import { Writes } from "../features/writes/Writes";
import { useConsole } from "../shared/api";
import type { Run } from "../shared/types";
import { Empty, ErrorState, Section, Segmented, Skeleton } from "../shared/ui";
import { motion as m, num, pct } from "./theme";

type Which = "dev" | "heldout";

export function headline(run: Run): string {
  const k = run.designs.kit;
  const g = run.designs.generic_mcp;
  return `${pct(k.accuracy)} of ${num(k.questions)} portfolio questions answered right with the kit. ${pct(g.accuracy)} when the assistant reads raw sheets.`;
}

function Desk({ run, names, patterns }: { run: Run; names: Record<string, string>; patterns: Record<string, string> }) {
  if (!run.customers.length || !run.designs.kit) return <Empty>This report has no customers. Run python3 scripts/evaluate.py, then python3 scripts/readme.py.</Empty>;
  const k = run.designs.kit;
  const g = run.designs.generic_mcp;
  const v = run.volume;
  return (
    <>
      <div className="hero">
        <AnimatePresence mode="wait" initial={false}>
          <motion.h1 key={run.world} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={m.swap}>
            {headline(run)}
          </motion.h1>
        </AnimatePresence>
        <p className="lede">
          {v.customers} customers, {num(v.sheets)} sheets, {num(v.rows)} rows. The kit drafts each customer's meanings from their own workspace, asks
          their admin {v.review_items} questions in all, settles the rules in one workshop and answers with code through the MCP server: {num(k.tokens_per_question)} tokens a
          question against {num(g.tokens_per_question)}.
        </p>
      </div>
      <Section id="translate" title="What the sheets mean at each customer" lede="Grey came from the sheets, violet from the customer's admin, teal from the workshop.">
        <Translate run={run} />
      </Section>
      <Section id="designs" title="The same questions, five ways of answering" lede={`A customer is accepted when the 95% lower bound on its share of right answers is at least ${pct(run.target, 0)}.`}>
        <Designs run={run} names={names} />
      </Section>
      <Section id="customers" title="Customer by customer">
        <Matrix run={run} names={names} />
      </Section>
      <Writes run={run} patterns={patterns} />
    </>
  );
}

export function App() {
  const q = useConsole();
  const [which, setWhich] = useState<Which>("dev");
  const run = q.data ? (which === "heldout" && q.data.heldout ? q.data.heldout : q.data.dev) : null;
  return (
    <div className="page">
      <header className="masthead">
        <span className="product">mcp-resource-packs</span>
        {q.data && (
          <Segmented<Which>
            label="Which world"
            options={(q.data.heldout ? { dev: "Dev world", heldout: "Held-out world" } : { dev: "Dev world" }) as Record<Which, string>}
            value={which}
            onChange={setWhich}
          />
        )}
      </header>
      <main>
        {q.isPending && <Skeleton />}
        {q.isError && <ErrorState message={(q.error as Error).message} onRetry={() => q.refetch()} />}
        {run && q.data && <Desk key={run.world} run={run} names={q.data.names} patterns={q.data.patterns} />}
      </main>
    </div>
  );
}
