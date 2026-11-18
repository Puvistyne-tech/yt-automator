import { screen, waitFor, within } from "@testing-library/react";
import { db } from "@/api/mocks/db";
import { renderApp } from "../helpers/renderApp";
import { audienceOf, openRun, uploadRows } from "../helpers/runs";

describe("Runs list", () => {
  it("lists runs and filters by status and automation through the url", async () => {
    const { user, router } = renderApp("/runs");
    const table = await screen.findByRole("table", { name: "Runs" });
    expect(within(table).getAllByRole("row")).toHaveLength(7);
    expect(within(table).getAllByRole("link", { name: "Tamil shorts" })).toHaveLength(3);

    await user.selectOptions(screen.getByLabelText("Status"), "failed");
    await waitFor(() =>
      expect(within(screen.getByRole("table", { name: "Runs" })).getAllByRole("row")).toHaveLength(
        2,
      ),
    );
    expect(router.state.location.search).toBe("?status=failed");

    await user.selectOptions(screen.getByLabelText("Automation"), "auto-bedtime");
    expect(await screen.findByText("No runs match these filters")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    await waitFor(() => expect(router.state.location.search).toBe(""));
  });

  it("shows an empty state without runs", async () => {
    db.state.runs = [];
    renderApp("/runs");

    expect(await screen.findByText("No runs yet")).toBeInTheDocument();
  });
});

describe("Run detail", () => {
  it("shows stages, artifacts grouped by language and output, and the score", async () => {
    const { user } = await openRun("run-review");

    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Bedtime stories");
    expect(await screen.findByText("English — Episode · 16:9")).toBeInTheDocument();
    expect(screen.getByText("Tamil — Episode · 16:9")).toBeInTheDocument();
    await user.click(screen.getByRole("tab", { name: "Score" }));
    expect(screen.getByRole("tabpanel")).toHaveTextContent("91.4");
    expect(screen.getByRole("tabpanel")).toHaveTextContent("Review rule: always");
  });

  it("shows the auto-approve review rule next to the score", async () => {
    await openRun("run-failed");

    expect(
      screen.getByText("auto-approve at 90+, reject under 60, publish on approval"),
    ).toBeInTheDocument();
  });

  it("shows why an upload was skipped", async () => {
    await openRun("run-published");

    const uploads = await screen.findByRole("table", { name: "Uploads" });
    expect(within(uploads).getByText("Skipped")).toBeInTheDocument();
    expect(within(uploads).getByText("Language ta is not in this run.")).toBeInTheDocument();
    expect(screen.getByText("1 uploaded · 1 failed · 0 pending · 1 skipped")).toBeInTheDocument();
  });

  it("shows the privacy and made-for-kids flag of each upload", async () => {
    await openRun("run-published");

    const rows = uploadRows(await screen.findByRole("table", { name: "Uploads" }));
    expect(audienceOf(rows, "Bedtime tales", "Episode")).toEqual(["Private", "Yes"]);
    expect(audienceOf(rows, "Bedtime tales", "Short")).toEqual(["Private", "Yes"]);
    expect(audienceOf(rows, "Kathai Neram", "Episode")).toEqual(["Unlisted", "Yes"]);
  });

  it("shows a dash for uploads stored before privacy was recorded", async () => {
    db.state.runs = db.state.runs.map((r) => ({
      ...r,
      uploads: r.uploads.map((u) => ({ ...u, privacy: null, made_for_kids: null })),
    }));
    await openRun("run-published");

    const rows = uploadRows(await screen.findByRole("table", { name: "Uploads" }));
    expect(audienceOf(rows, "Kathai Neram", "Episode")).toEqual(["—", "—"]);
  });

  it("shows an empty log for a run without log lines", async () => {
    const { user } = await openRun("run-review");
    await user.click(screen.getByRole("tab", { name: "Logs" }));

    expect(screen.getByText("No log lines yet")).toBeInTheDocument();
    expect(screen.getByText("Log lines appear here as the run progresses.")).toBeInTheDocument();
  });

  it("styles stored log lines by level and names their stage", async () => {
    const { user } = await openRun("run-failed");
    await user.click(screen.getByRole("tab", { name: "Logs" }));

    const line = (text: string) => screen.getByText(text).closest(".log-line");
    const failed = line("No text-to-speech provider can speak Tamil");
    expect(failed).toHaveAttribute("data-level", "error");
    expect(failed).toHaveTextContent("Narrate");
    expect(line("Kokoro has no Tamil voice, trying the next provider")).toHaveAttribute(
      "data-level",
      "warning",
    );
    const runLine = line("Run failed");
    expect(runLine).toHaveAttribute("data-level", "info");
    expect(runLine?.querySelector(".log-stage")).toHaveTextContent(/^Run$/);
  });

  it("shows an error state for an unknown run", async () => {
    renderApp("/runs/nope");

    expect(await screen.findByText("run 'nope' was not found")).toBeInTheDocument();
  });
});
