#!/usr/bin/env node
/**
 * Runs the server on stdio for one customer.
 *   PACK=kits/C01/pack.json SNAPSHOT=data/example/workspace.json node dist/main.js
 *   PACK=... SMARTSHEET_TOKEN=... node dist/main.js
 */
import { readFile } from "node:fs/promises";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { createServer } from "./server.js";
import { SmartsheetSource, SnapshotSource, type Source } from "./source.js";
import type { Pack } from "./types.js";

const env = process.env;
if (!env.PACK) {
  console.error("Set PACK to the customer's pack.json, and SNAPSHOT or SMARTSHEET_TOKEN.");
  process.exit(2);
}
const pack = JSON.parse(await readFile(env.PACK, "utf8")) as Pack;
let source: Source;
if (env.SNAPSHOT) source = new SnapshotSource(env.SNAPSHOT);
else if (env.SMARTSHEET_TOKEN) source = new SmartsheetSource(env.SMARTSHEET_TOKEN, pack.customer);
else {
  console.error("Set SNAPSHOT to a workspace file or SMARTSHEET_TOKEN to read the live workspace.");
  process.exit(2);
}
const today = env.TODAY ? () => env.TODAY as string : undefined;
await createServer(pack, source, { today }).connect(new StdioServerTransport());
