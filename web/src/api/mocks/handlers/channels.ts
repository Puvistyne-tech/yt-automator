import { HttpResponse, http } from "msw";
import { apiError, db, noContent, notFound } from "@/api/mocks/db";
import type { ChannelDefaults, CredentialInput, CredentialSummary } from "@/api/types";

function credentialErrors(input: Partial<CredentialInput>, creating: boolean) {
  const errors: Record<string, string> = {};
  if (creating && !input.name?.trim()) {
    errors.name = "Name is required.";
  }
  if (creating && !input.client_id?.trim()) {
    errors.client_id = "Client id is required.";
  }
  return errors;
}

function publicCredential(credential: CredentialSummary) {
  const { has_secret: _secret, quota_used_today: _used, ...rest } = credential;
  return rest;
}

function patchCredential(credential: CredentialSummary, input: Partial<CredentialInput>) {
  const { client_secret, ...fields } = input;
  return {
    ...credential,
    ...fields,
    has_secret: credential.has_secret || (client_secret ?? "") !== "",
  };
}

export const channelHandlers = [
  http.get("/api/credentials", () => HttpResponse.json(db.state.credentials)),
  http.post("/api/credentials", async ({ request }) => {
    const input = (await request.json()) as CredentialInput;
    const errors = credentialErrors(input, true);
    if (Object.keys(errors).length > 0) {
      return apiError(400, "validation_error", "The credential is not valid.", errors);
    }
    const credential: CredentialSummary = {
      id: db.id("cred"),
      name: input.name,
      client_id: input.client_id,
      daily_quota_units: input.daily_quota_units ?? 10_000,
      created_at: db.now(),
      has_secret: input.client_secret !== "",
      quota_used_today: 0,
    };
    db.state.credentials = [...db.state.credentials, credential];
    return HttpResponse.json(publicCredential(credential), { status: 201 });
  }),
  http.patch("/api/credentials/:id", async ({ params, request }) => {
    const credential = db.state.credentials.find((c) => c.id === params.id);
    if (credential === undefined) {
      return notFound("Credential");
    }
    const updated = patchCredential(credential, (await request.json()) as Partial<CredentialInput>);
    db.state.credentials = db.state.credentials.map((c) => (c.id === updated.id ? updated : c));
    return HttpResponse.json(publicCredential(updated));
  }),
  http.delete("/api/credentials/:id", ({ params }) => {
    if (db.state.channels.some((channel) => channel.credential_id === params.id)) {
      return apiError(
        409,
        "credential_in_use",
        "Disconnect the channels using this credential first.",
      );
    }
    db.state.credentials = db.state.credentials.filter((c) => c.id !== params.id);
    return noContent();
  }),
  http.get("/api/channels", () => HttpResponse.json(db.state.channels)),
  http.post("/api/channels/connect", async ({ request }) => {
    const { credential_id } = (await request.json()) as { credential_id: string };
    return HttpResponse.json({
      authorization_url: `${window.location.origin}/channels?connected=chan-en&credential=${credential_id}`,
    });
  }),
  http.patch("/api/channels/:id", async ({ params, request }) => {
    const channel = db.state.channels.find((c) => c.id === params.id);
    if (channel === undefined) {
      return notFound("Channel");
    }
    const { defaults } = (await request.json()) as { defaults: ChannelDefaults };
    const updated = { ...channel, defaults };
    db.state.channels = db.state.channels.map((c) => (c.id === updated.id ? updated : c));
    return HttpResponse.json(updated);
  }),
  http.delete("/api/channels/:id", ({ params }) => {
    const used = db.state.automations.some(
      (a) => a.enabled && a.targets.some((target) => target.channel_id === params.id),
    );
    if (used) {
      return apiError(
        409,
        "channel_in_use",
        "An enabled automation still publishes to this channel.",
      );
    }
    db.state.channels = db.state.channels.filter((c) => c.id !== params.id);
    return noContent();
  }),
  http.get("/api/channels/:id/playlists", ({ params }) =>
    HttpResponse.json(db.state.playlists[String(params.id)] ?? []),
  ),
];
