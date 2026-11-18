import { makeChannel, makeCredential } from "@/api/mocks/fixtures/factories";
import {
  credentialPayload,
  credentialSecretHint,
  credentialValues,
  validateCredential,
} from "@/features/channels/credentialForm";
import { channelDefaultsPayload, validateChannelDefaults } from "@/features/channels/defaultsForm";
import {
  oauthErrorMessage,
  oauthReturnMessage,
  withoutOAuthParams,
} from "@/features/channels/oauthReturn";
import { validateSecretValue } from "@/features/secrets/secretForm";

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

  it.each([0, 2.5])("rejects a daily quota of %d on its own", (daily_quota_units) => {
    expect(validateCredential({ ...values, daily_quota_units }, false)).toEqual({
      daily_quota_units: "Use a whole number of units, at least 1.",
    });
  });

  it("hints at the stored secret state", () => {
    expect(credentialSecretHint(undefined)).toBe(
      "Stored in the keychain. It is never shown again.",
    );
    expect(credentialSecretHint(makeCredential())).toBe(
      "A secret is stored. Leave blank to keep it.",
    );
    expect(credentialSecretHint(makeCredential({ has_secret: false }))).toBe(
      "No secret stored yet.",
    );
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
  const title = (id: string) => (id === "chan-en" ? "Bedtime tales" : undefined);

  it.each([
    ["connected=chan-en", { tone: "success", message: "Connected Bedtime tales." }],
    ["connected=other", { tone: "success", message: "Channel connected." }],
    [
      "error=access_denied",
      { tone: "error", message: "Google sign-in was cancelled, so no channel was connected." },
    ],
    [
      "error=youtube_scope_denied",
      {
        tone: "error",
        message:
          "Google granted fewer permissions than needed. Connect again and allow every permission.",
      },
    ],
    [
      "error=some_new_code",
      { tone: "error", message: "Connecting the channel failed: some new code." },
    ],
    ["connected=chan-en&error=x", { tone: "success", message: "Connected Bedtime tales." }],
    ["", null],
  ])("reads ?%s", (query, expected) => {
    expect(oauthReturnMessage(new URLSearchParams(query), title)).toEqual(expected);
  });

  it.each([
    ["missing_code", "Google did not send an authorization code. Start connecting again."],
    [
      "validation_failed",
      "The sign-in link was invalid or expired, or its credential was changed or removed. Start connecting again.",
    ],
    [
      "youtube_no_channel",
      "That Google account has no YouTube channel. Choose an account that owns one.",
    ],
    [
      "youtube_oauth_failed",
      "Google rejected the sign-in. Check the credential's client id and secret, then try again.",
    ],
    ["youtube_invalid_grant", "Google refused the authorization code. Start connecting again."],
    [
      "youtube_unreachable",
      "Google could not be reached. Check the internet connection and try again.",
    ],
    [
      "youtube_quota_exceeded",
      "The credential's YouTube quota is used up for today. Try again after midnight Pacific time.",
    ],
    ["credential_secret_missing", "Add the credential's client secret, then connect again."],
    [
      "secrets_unreadable",
      "Stored secrets could not be read. The error on the Google API credentials card names the files to remove; remove them, then reconnect.",
    ],
  ])("explains the %s return code in plain words", (code, message) => {
    expect(oauthErrorMessage(code)).toBe(message);
  });

  it("has no message for a code the backend never sends", () => {
    expect(oauthErrorMessage("credential_not_found")).toBe(
      "Connecting the channel failed: credential not found.",
    );
  });

  it("strips only the oauth parameters from the url", () => {
    const params = new URLSearchParams("connected=a&error=b&tab=x");
    expect(withoutOAuthParams(params).toString()).toBe("tab=x");
  });
});

describe("channel defaults form", () => {
  const defaults = makeChannel().defaults;

  it("requires category and language", () => {
    expect(validateChannelDefaults(defaults)).toEqual({});
    expect(
      validateChannelDefaults({ ...defaults, category_id: " ", default_language: "" }),
    ).toEqual({ category_id: "Required.", default_language: "Required." });
  });

  it("trims the codes it sends", () => {
    expect(
      channelDefaultsPayload({ ...defaults, category_id: " 1 ", default_language: " ta " }),
    ).toMatchObject({ category_id: "1", default_language: "ta" });
  });
});

describe("secret form", () => {
  it("trims the value and rejects blanks", () => {
    expect(validateSecretValue("  ")).toEqual({ ok: false, error: "Enter a value." });
    expect(validateSecretValue(" key ")).toEqual({ ok: true, value: "key" });
  });
});
