import { HttpResponse, http } from "msw";
import { connectReturnUrl } from "@/api/mocks/connect";
import { db, noContent, notFound, ruleConflict, validationFailed } from "@/api/mocks/db";
import type { ChannelDefaults, CredentialInput, CredentialView } from "@/api/types";

const MIN_LENGTH = "String should have at least 1 character";

function credentialErrors(input: Partial<CredentialInput>, creating: boolean) {
  const errors: Record<string, string> = {};
  const fields = ["name", "client_id", "client_secret"] as const;
  for (const field of fields) {
    const value = input[field];
    if ((creating && value === undefined) || value === "") {
      errors[field] = value === undefined ? "Field required" : MIN_LENGTH;
    }
  }
  return errors;
}

function patchCredential(credential: CredentialView, input: Partial<CredentialInput>) {
  const { client_secret, ...fields } = input;
  return {
    ...credential,
    ...fields,
    has_secret: credential.has_secret || (client_secret ?? "") !== "",
  };
}

function createCredential(input: CredentialInput): CredentialView {
  return {
    id: db.id("cred"),
    name: input.name,
    client_id: input.client_id,
    daily_quota_units: input.daily_quota_units ?? 10_000,
    created_at: db.now(),
    has_secret: true,
    quota_used_today: 0,
  };
}

const credentialHandlers = [
  http.get("/api/credentials", () => HttpResponse.json(db.state.credentials)),
  http.post("/api/credentials", async ({ request }) => {
    const input = (await request.json()) as CredentialInput;
    const errors = credentialErrors(input, true);
    if (Object.keys(errors).length > 0) {
      return validationFailed(errors);
    }
    const credential = createCredential(input);
    db.state.credentials = [...db.state.credentials, credential];
    return HttpResponse.json(credential, { status: 201 });
  }),
  http.patch("/api/credentials/:id", async ({ params, request }) => {
    const credential = db.state.credentials.find((c) => c.id === params.id);
    if (credential === undefined) {
      return notFound("credential", params.id);
    }
    const input = (await request.json()) as Partial<CredentialInput>;
    const errors = credentialErrors(input, false);
    if (Object.keys(errors).length > 0) {
      return validationFailed(errors);
    }
    const updated = patchCredential(credential, input);
    db.state.credentials = db.state.credentials.map((c) => (c.id === updated.id ? updated : c));
    return HttpResponse.json(updated);
  }),
  http.delete("/api/credentials/:id", ({ params }) => {
    const using = db.state.channels.filter((channel) => channel.credential_id === params.id);
    if (using.length > 0) {
      const titles = using.map((channel) => channel.title).sort();
      return ruleConflict(
        "credential_in_use",
        `credential is used by channels: ${titles.join(", ")}`,
      );
    }
    db.state.credentials = db.state.credentials.filter((c) => c.id !== params.id);
    return noContent();
  }),
];

const channelHandlers = [
  http.get("/api/channels", () => HttpResponse.json(db.state.channels)),
  http.post("/api/channels/connect", async ({ request }) => {
    const { credential_id } = (await request.json()) as { credential_id: string };
    const credential = db.state.credentials.find((c) => c.id === credential_id);
    if (credential === undefined) {
      return notFound("credential", credential_id);
    }
    if (!credential.has_secret) {
      return ruleConflict(
        "credential_secret_missing",
        `credential ${credential_id} has no client secret`,
      );
    }
    return HttpResponse.json({ authorization_url: connectReturnUrl(credential_id) });
  }),
  http.patch("/api/channels/:id", async ({ params, request }) => {
    const channel = db.state.channels.find((c) => c.id === params.id);
    if (channel === undefined) {
      return notFound("channel", params.id);
    }
    const { defaults } = (await request.json()) as { defaults: ChannelDefaults };
    const updated = { ...channel, defaults };
    db.state.channels = db.state.channels.map((c) => (c.id === updated.id ? updated : c));
    return HttpResponse.json(updated);
  }),
  http.delete("/api/channels/:id", ({ params }) => {
    const blocking = db.state.automations
      .filter((a) => a.enabled && a.targets.some((target) => target.channel_id === params.id))
      .map((a) => a.name)
      .sort();
    if (blocking.length > 0) {
      return ruleConflict(
        "channel_in_use",
        `channel is targeted by enabled automations: ${blocking.join(", ")}`,
      );
    }
    db.state.channels = db.state.channels.filter((c) => c.id !== params.id);
    return noContent();
  }),
  http.get("/api/channels/:id/playlists", ({ params }) =>
    HttpResponse.json(db.state.playlists[String(params.id)] ?? []),
  ),
];

export { channelHandlers, credentialHandlers };
