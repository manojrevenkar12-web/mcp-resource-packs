import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import raw from "../../public/data/console.json";
import type { Console } from "../shared/types";
import { App, headline } from "./App";

const data = raw as unknown as Console;

function mount() {
  return render(
    <QueryClientProvider client={new QueryClient()}>
      <App />
    </QueryClientProvider>,
  );
}

const ok = (body: unknown) => Promise.resolve(new Response(JSON.stringify(body), { status: 200 }));
const h1 = () => screen.getByRole("heading", { level: 1 }).textContent;

afterEach(() => vi.unstubAllGlobals());

describe("console", () => {
  it("shows a skeleton while the report loads", () => {
    vi.stubGlobal("fetch", () => new Promise(() => {}));
    mount();
    expect(screen.getByLabelText("Loading")).toBeTruthy();
  });

  it("explains a failed load and retries", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValueOnce(new Response("", { status: 500 })).mockImplementation(() => ok(data)));
    mount();
    await screen.findByRole("alert");
    fireEvent.click(screen.getByText("Retry"));
    await waitFor(() => expect(h1()).toBe(headline(data.dev)));
  });

  it("says what to do when the report has no customers", async () => {
    vi.stubGlobal("fetch", () => ok({ ...data, dev: { ...data.dev, customers: [] } }));
    mount();
    expect(await screen.findByText(/has no customers/)).toBeTruthy();
  });

  it("leads with the kit beating raw sheets", () => {
    expect(data.dev.designs.kit.accuracy).toBeGreaterThan(data.dev.designs.generic_mcp.accuracy);
    expect(headline(data.dev)).toContain(String(data.dev.designs.kit.questions));
  });

  it("switches customer and shows what their sheets mean, with who said so", async () => {
    vi.stubGlobal("fetch", () => ok(data));
    mount();
    await screen.findByRole("heading", { level: 1 });
    const other = data.dev.customers.find((c) => c.translations.some((t) => t.source === "admin") && c.id !== "C08")!;
    fireEvent.click(screen.getByRole("button", { name: other.id }));
    const t = other.translations.find((x) => x.source === "admin")!;
    expect(await screen.findAllByText(t.seen)).not.toHaveLength(0);
    expect(screen.getAllByText("confirmed by the admin").length).toBeGreaterThan(0);
  });

  it("marks each customer accepted or not for every design", async () => {
    vi.stubGlobal("fetch", () => ok(data));
    mount();
    await screen.findByRole("heading", { level: 1 });
    const accepted = data.dev.customers.reduce((a, c) => a + Object.values(c.designs).filter((d) => d.accepted).length, 0);
    expect(screen.getAllByLabelText(/, accepted$/).length).toBe(accepted);
  });

  it("offers the held-out world only when it exists", async () => {
    vi.stubGlobal("fetch", () => ok({ ...data, heldout: null }));
    mount();
    await screen.findByRole("heading", { level: 1 });
    expect(screen.queryByText("Held-out world")).toBeNull();
  });
});
