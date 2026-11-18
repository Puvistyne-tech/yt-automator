export interface OAuthReturnMessage {
  tone: "success" | "error";
  message: string;
}

export const OAUTH_RETURN_PARAMS = ["connected", "error", "credential"];

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
    return {
      tone: "error",
      message: `Connecting the channel failed: ${error.replace(/_/g, " ")}.`,
    };
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
