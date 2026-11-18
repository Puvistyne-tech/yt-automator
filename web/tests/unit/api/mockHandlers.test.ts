import { api } from "@/api/client";
import { completeConnectReturn } from "@/api/mocks/connect";
import { db, EMPTY_VALUE_MESSAGE } from "@/api/mocks/db";
import type { Run } from "@/api/types";

const failure = (call: Promise<unknown>) =>
  call.then(
    () => null,
    (error: unknown) => error,
  );
const channelStatus = (id: string) => db.state.channels.find((c) => c.id === id)?.status;

describe("mock credential handlers", () => {
  it("requires every field when adding a credential", async () => {
    expect(await failure(api.post("/credentials", {}))).toMatchObject({
      status: 400,
      code: "validation_failed",
      fields: {
        name: "Field required",
        client_id: "Field required",
        client_secret: "Field required",
      },
    });
  });

  it("refuses an empty value when changing a credential", async () => {
    expect(await failure(api.patch("/credentials/cred-main", { name: "" }))).toMatchObject({
      status: 400,
      fields: { name: EMPTY_VALUE_MESSAGE },
    });
  });

  it.each([
    ["/credentials/missing", "credential_not_found"],
    ["/channels/missing", "channel_not_found"],
    ["/automations/missing", "automation_not_found"],
  ])("returns 404 when deleting the unknown %s", async (path, code) => {
    expect(await failure(api.delete(path))).toMatchObject({ status: 404, code });
  });
});

describe("mock connect flow", () => {
  it.each([
    ["nope", 404, "credential_not_found"],
    ["cred-spare", 409, "credential_secret_missing"],
  ])("refuses to connect with credential %s", async (credential_id, status, code) => {
    const error = await failure(api.post("/channels/connect", { credential_id }));
    expect(error).toMatchObject({ status, code });
  });

  it("picks the credential's expired channel and reconnects it only on return", async () => {
    const started = await api.post<{ authorization_url: string }>("/channels/connect", {
      credential_id: "cred-main",
    });
    const url = new URL(started.authorization_url);
    expect(url.pathname).toBe("/channels");
    expect([...url.searchParams.keys()]).toEqual(["connected"]);
    expect(channelStatus("chan-old")).toBe("expired");

    completeConnectReturn(url.search);

    expect(channelStatus("chan-old")).toBe("connected");
  });

  it("connects the default channel when the credential has no expired channel", async () => {
    db.state.channels = db.state.channels.filter((channel) => channel.id !== "chan-old");
    const started = await api.post<{ authorization_url: string }>("/channels/connect", {
      credential_id: "cred-main",
    });
    expect(new URL(started.authorization_url).searchParams.get("connected")).toBe("chan-en");
  });
});

describe("mock automation and run handlers", () => {
  it("reports an empty name, an unknown pipeline and a missing channel", async () => {
    const automation = db.state.automations[0];
    const input = { ...automation, name: "", pipeline_type: "nope" };
    expect(await failure(api.post("/automations", input))).toMatchObject({
      status: 400,
      fields: {
        name: EMPTY_VALUE_MESSAGE,
        pipeline_type: "unknown pipeline type 'nope'",
      },
    });
  });

  it("checks the run's status before the stage when retrying", async () => {
    expect(await failure(api.post("/runs/run-live/retry", { from_stage: "zzz" }))).toMatchObject({
      status: 409,
      code: "invalid_run_transition",
    });
    expect(await failure(api.post("/runs/run-failed/retry", { from_stage: "zzz" }))).toMatchObject({
      status: 400,
      fields: { from_stage: "run has no stage 'zzz'" },
    });
  });

  it("resets the retried stages and clears the run's results like the backend", async () => {
    const run = await api.post<Run>("/runs/run-review/retry", { from_stage: "render" });
    const render = run.stages.find((stage) => stage.stage_id === "render");
    expect(render).toMatchObject({ status: "pending", provider: "", message: "" });
    expect(render).toMatchObject({ started_at: null, finished_at: null });
    expect(run.stages[0]?.status).toBe("done");
    expect(run.artifacts.some((artifact) => artifact.stage_id === "render")).toBe(false);
    expect(run).toMatchObject({ status: "queued", score: null, review: null, uploads: [] });
    expect(run).toMatchObject({ score_details: [], error: null, started_at: null });
  });

  it("retries from the first unfinished stage by default", async () => {
    const run = await api.post<Run>("/runs/run-failed/retry", {});
    expect(run).toMatchObject({ auto_retries: 0, retry_at: null });
    expect(run.stages.map((stage) => stage.status)).toEqual([
      "done",
      "done",
      "done",
      "pending",
      "pending",
      "pending",
    ]);
  });
});
