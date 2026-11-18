import { api, apiUrl, request, requestText } from "@/api/client";
import { ApiError } from "@/api/errors";

function stubFetch(response: Response | Error) {
  return vi
    .spyOn(globalThis, "fetch")
    .mockImplementation(() =>
      response instanceof Error ? Promise.reject(response) : Promise.resolve(response),
    );
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("api client", () => {
  it("turns an unreachable server into a network error", async () => {
    stubFetch(new TypeError("Failed to fetch"));
    const error = await api.get("/health").catch((caught: unknown) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error).toMatchObject({ status: 0, code: "network_error" });
  });

  it("returns null for an empty 204 body", async () => {
    stubFetch(new Response(null, { status: 204 }));
    await expect(api.delete("/runs/x")).resolves.toBeNull();
  });

  it("returns raw text when the body is not json", async () => {
    stubFetch(new Response("plain words", { status: 200 }));
    await expect(request<string>("GET", "/x")).resolves.toBe("plain words");
  });

  it("names the request id of an unexpected server error", async () => {
    const body = {
      error: { code: "internal_error", message: "Unexpected server error", fields: {} },
    };
    stubFetch(
      new Response(JSON.stringify(body), { status: 500, headers: { "X-Request-Id": "ab12" } }),
    );
    await expect(api.get("/x")).rejects.toMatchObject({
      code: "internal_error",
      message: "Unexpected server error (request id ab12)",
    });
  });

  it("falls back to a generic message for an html error page", async () => {
    stubFetch(new Response("<html>bad gateway</html>", { status: 502 }));
    await expect(api.get("/x")).rejects.toMatchObject({
      status: 502,
      code: "http_502",
      message: "Request failed",
    });
  });

  it("sends json bodies with a content type", async () => {
    const spy = stubFetch(new Response("{}", { status: 200 }));
    await api.post("/x", { a: 1 });
    const init = spy.mock.calls[0]?.[1];
    expect(init?.body).toBe('{"a":1}');
    expect(init?.headers).toMatchObject({ "Content-Type": "application/json" });
  });

  it("throws from requestText on a failed response", async () => {
    stubFetch(new Response("missing", { status: 404 }));
    await expect(requestText("/runs/x/artifacts/y")).rejects.toMatchObject({
      status: 404,
      message: "Could not load file",
    });
  });

  it("returns the text of a successful requestText", async () => {
    stubFetch(new Response("WEBVTT", { status: 200 }));
    await expect(requestText("/runs/x/artifacts/y")).resolves.toBe("WEBVTT");
  });

  it("drops empty and undefined query values", () => {
    expect(new URL(apiUrl("/x", { a: "", b: undefined, c: 1 })).search).toBe("?c=1");
    expect(new URL(apiUrl("/x")).pathname).toBe("/api/x");
  });
});
