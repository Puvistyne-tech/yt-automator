export interface OAuthReturnMessage {
  tone: "success" | "error";
  message: string;
}

export const OAUTH_RETURN_PARAMS = ["connected", "error"];

const OAUTH_ERROR_MESSAGES: Record<string, string> = {
  access_denied: "Google sign-in was cancelled, so no channel was connected.",
  missing_code: "Google did not send an authorization code. Start connecting again.",
  validation_failed:
    "The sign-in link was invalid or expired, or its credential was changed or removed. Start connecting again.",
  youtube_scope_denied:
    "Google granted fewer permissions than needed. Connect again and allow every permission.",
  youtube_no_channel:
    "That Google account has no YouTube channel. Choose an account that owns one.",
  youtube_oauth_failed:
    "Google rejected the sign-in. Check the credential's client id and secret, then try again.",
  youtube_invalid_grant: "Google refused the authorization code. Start connecting again.",
  youtube_unreachable: "Google could not be reached. Check the internet connection and try again.",
  credential_secret_missing: "Add the credential's client secret, then connect again.",
  youtube_quota_exceeded:
    "The credential's YouTube quota is used up for today. Try again after midnight Pacific time.",
  secrets_unreadable:
    "Stored secrets could not be read. The error on the Google API credentials card names the files to remove; remove them, then reconnect.",
};

export function oauthErrorMessage(code: string): string {
  return OAUTH_ERROR_MESSAGES[code] ?? `Connecting the channel failed: ${code.replace(/_/g, " ")}.`;
}

export function oauthReturnMessage(
  params: URLSearchParams,
  channelTitle: (id: string) => string | undefined,
): OAuthReturnMessage | null {
  const connected = params.get("connected");
  const error = params.get("error");
  if (connected !== null) {
    const title = channelTitle(connected);
    return { tone: "success", message: title ? `Connected ${title}.` : "Channel connected." };
  }
  if (error !== null) {
    return { tone: "error", message: oauthErrorMessage(error) };
  }
  return null;
}

export function withoutOAuthParams(params: URLSearchParams): URLSearchParams {
  const next = new URLSearchParams(params);
  for (const key of OAUTH_RETURN_PARAMS) {
    next.delete(key);
  }
  return next;
}
