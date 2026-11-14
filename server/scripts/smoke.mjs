// Starts the built server on stdio the way an AI tool does, and asks it one question.
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: "node",
  args: ["dist/main.js"],
  env: { ...process.env, PACK: "../data/example/pack.json", SNAPSHOT: "../data/example/workspace.json", TODAY: "2026-11-16" },
});
const client = new Client({ name: "smoke", version: "0" });
await client.connect(transport);
const tools = (await client.listTools()).tools.map((t) => t.name);
const r = await client.callTool({ name: "portfolio_query", arguments: { op: "list", entity: "projects", where: { at_risk: true } } });
const { answer } = JSON.parse(r.content[0].text);
console.log(`tools: ${tools.join(", ")}; projects at risk: ${answer.length}`);
await client.close();
if (!tools.includes("portfolio_query") || !Array.isArray(answer)) process.exit(1);
