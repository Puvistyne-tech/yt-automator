import { HttpResponse, http } from "msw";
import { apiError, db, noContent, notFound } from "@/api/mocks/db";
import type { AppSettingsInput, Dashboard, ProviderConfig } from "@/api/types";

function dashboard(): Dashboard {
  const { automations, channels, runs, credentials } = db.state;
  const today = new Date().toISOString().slice(0, 10);
  return {
    automations: automations.length,
    enabled_automations: automations.filter((a) => a.enabled).length,
    channels: channels.length,
    runs_awaiting_review: runs.filter((r) => r.status === "awaiting_review").length,
    runs_today: runs.filter((r) => r.created_at.startsWith(today)).length,
    recent_runs: runs.slice(0, 8).map((run) => ({
      id: run.id,
      status: run.status,
      score: run.score,
      created_at: run.created_at,
      finished_at: run.finished_at,
      automation_name: run.automation_name,
    })),
    quota: credentials.map((c) => ({
      credential_id: c.id,
      name: c.name,
      used: c.quota_used_today,
      limit: c.daily_quota_units,
    })),
  };
}

function setSecret(name: string, isSet: boolean) {
  db.state.secrets = db.state.secrets.map((s) => (s.name === name ? { ...s, is_set: isSet } : s));
  db.state.descriptors = db.state.descriptors.map((d) =>
    d.required_secrets.includes(name)
      ? { ...d, available: isSet, unavailable_reason: isSet ? null : `Secret ${name} is not set.` }
      : d,
  );
}

export const systemHandlers = [
  http.get("/api/health", () => HttpResponse.json({ status: "ok", version: "0.1.0-mock" })),
  http.get("/api/dashboard", () => HttpResponse.json(dashboard())),
  http.get("/api/pipelines", () => HttpResponse.json(db.state.pipelines)),
  http.get("/api/pipelines/:typeId", ({ params }) => {
    const pipeline = db.state.pipelines.find((p) => p.type_id === params.typeId);
    return pipeline ? HttpResponse.json(pipeline) : notFound("Pipeline");
  }),
  http.get("/api/providers", () =>
    HttpResponse.json({ descriptors: db.state.descriptors, config: db.state.providerConfig }),
  ),
  http.put("/api/providers", async ({ request }) => {
    db.state.providerConfig = (await request.json()) as ProviderConfig[];
    return HttpResponse.json(db.state.providerConfig);
  }),
  http.get("/api/secrets", () => HttpResponse.json(db.state.secrets)),
  http.put("/api/secrets/:name", async ({ params, request }) => {
    const { value } = (await request.json()) as { value: string };
    if (value === "") {
      return apiError(400, "validation_error", "A value is required.", { value: "Enter a value." });
    }
    setSecret(String(params.name), true);
    return noContent();
  }),
  http.delete("/api/secrets/:name", ({ params }) => {
    setSecret(String(params.name), false);
    return noContent();
  }),
  http.get("/api/settings", () => HttpResponse.json(db.state.settings)),
  http.put("/api/settings", async ({ request }) => {
    const input = (await request.json()) as AppSettingsInput;
    db.state.settings = { ...db.state.settings, ...input };
    return HttpResponse.json(db.state.settings);
  }),
];
