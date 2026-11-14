/** Numbers the components use. Colours and spacing live in tokens.css. */
export const motion = {
  bar: { duration: 0.55, ease: [0.25, 0.1, 0.25, 1] as const },
  swap: { duration: 0.18 },
  row: { duration: 0.22 },
  stagger: 0.035,
};

export const order = ["generic_mcp", "pack_as_context", "drafted_pack", "reviewed_pack", "kit"] as const;
export const skeletonRows = 4;
export const skeletonStep = 12;
export const firstCustomer = "C08";
/** Token axis: log scale from 100 to 100,000 tokens. */
export const tokenAxis = { min: 2, max: 5 };

export const pct = (x: number, digits = 1) => `${(x * 100).toFixed(digits)}%`;
export const eur = (x: number) => `€${x.toFixed(2)}`;
export const num = (x: number) => x.toLocaleString("en-GB");
