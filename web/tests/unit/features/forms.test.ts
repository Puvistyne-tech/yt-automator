import { makeCredential } from "@/api/mocks/fixtures/factories";
import { settingsInput, validateSettings } from "@/features/app-settings/validate";
import {
  credentialPayload,
  credentialValues,
  oauthReturnMessage,
  validateCredential,
} from "@/features/channels/credentialForm";

const values = { name: " Main ", client_id: " id ", client_secret: "", daily_quota_units: 500 };

describe("credential form", () => {
  it("starts from defaults or an existing credential without its secret", () => {
    expect(credentialValues(undefined)).toEqual({
      name: "",
      client_id: "",
      client_secret: "",
      daily_quota_units: 10_000,
    });
    expect(credentialValues(makeCredential())).toMatchObject({
      name: "Main Google project",
      client_secret: "",
    });
  });

  it("requires a secret only for new credentials", () => {
    expect(validateCredential(values, false)).toEqual({});
    expect(validateCredential(values, true)).toEqual({
      client_secret: "Paste the OAuth client secret.",
    });
  });

  it("reports every missing field", () => {
    const empty = { name: "", client_id: " ", client_secret: "", daily_quota_units: 0.5 };
    expect(Object.keys(validateCredential(empty, true)).sort()).toEqual([
      "client_id",
      "client_secret",
      "daily_quota_units",
      "name",
    ]);
  });

  it("sends the secret only when one was typed", () => {
    expect(credentialPayload(values, false)).toEqual({
      name: "Main",
      client_id: "id",
      daily_quota_units: 500,
    });
    expect(credentialPayload({ ...values, client_secret: " s " }, false)).toMatchObject({
      client_secret: "s",
    });
    expect(credentialPayload(values, true)).toMatchObject({ client_secret: "" });
  });
});

describe("oauthReturnMessage", () => {
  const title = (id: string) => (id === "chan-en" ? "Kutty Stories" : undefined);

  it.each([
    ["connected=chan-en", { tone: "success", message: "Connected Kutty Stories." }],
    ["connected=other", { tone: "success", message: "Channel connected." }],
    [
      "error=access_denied",
      { tone: "error", message: "Connecting the channel failed: access denied." },
    ],
    ["", null],
  ])("reads ?%s", (query, expected) => {
    expect(oauthReturnMessage(new URLSearchParams(query), title)).toEqual(expected);
  });
});

describe("app settings", () => {
  const settings = { timezone: "UTC", max_parallel_runs: 2, keep_runs_days: 30, data_dir: "/d" };

  it("drops read-only fields from the input", () => {
    expect(settingsInput(settings)).toEqual({
      timezone: "UTC",
      max_parallel_runs: 2,
      keep_runs_days: 30,
    });
  });

  it.each([
    [{ timezone: "" }, { timezone: "Choose a timezone." }],
    [{ max_parallel_runs: 0 }, { max_parallel_runs: "Use a whole number, at least 1." }],
    [{ keep_runs_days: 1.5 }, { keep_runs_days: "Keep runs for at least 1 day." }],
    [{}, {}],
  ])("validates %j", (patch, errors) => {
    expect(validateSettings({ ...settingsInput(settings), ...patch })).toEqual(errors);
  });
});
