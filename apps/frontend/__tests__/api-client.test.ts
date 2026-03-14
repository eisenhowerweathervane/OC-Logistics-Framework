/**
 * Tests for the ApiClient class in src/lib/api.ts
 *
 * We re-import the module per test group so we can control
 * localStorage and global fetch independently.
 */

beforeEach(() => {
  jest.resetModules();
  localStorage.clear();
  jest.restoreAllMocks();
});

// Helper: build a minimal Response
function jsonResponse(body: unknown, status = 200): Response {
  return {
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
    headers: new Headers(),
    redirected: false,
    statusText: status === 200 ? "OK" : "Error",
    type: "basic" as ResponseType,
    url: "",
    clone: () => jsonResponse(body, status) as Response,
    body: null,
    bodyUsed: false,
    arrayBuffer: () => Promise.resolve(new ArrayBuffer(0)),
    blob: () => Promise.resolve(new Blob()),
    formData: () => Promise.resolve(new FormData()),
    text: () => Promise.resolve(JSON.stringify(body)),
    bytes: () => Promise.resolve(new Uint8Array()),
  } as Response;
}

describe("ApiClient", () => {
  it("includes Authorization header when token is in localStorage", async () => {
    const fetchSpy = jest.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ ok: true }),
    );

    localStorage.setItem("access_token", "my_token");

    // Dynamic import so localStorage is already set
    const { api } = await import("@/lib/api");

    await api.get("/api/test");

    expect(fetchSpy).toHaveBeenCalledTimes(1);
    const [url, options] = fetchSpy.mock.calls[0];
    expect(url).toContain("/api/test");
    expect((options as RequestInit).headers).toEqual(
      expect.objectContaining({ Authorization: "Bearer my_token" }),
    );
  });

  it("does not include Authorization header when no token exists", async () => {
    const fetchSpy = jest.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ ok: true }),
    );

    // Clear to be sure
    localStorage.removeItem("access_token");

    const { api } = await import("@/lib/api");

    await api.get("/api/test");

    const [, options] = fetchSpy.mock.calls[0];
    expect((options as RequestInit).headers).not.toHaveProperty("Authorization");
  });

  it("attempts token refresh on 401 response", async () => {
    localStorage.setItem("access_token", "expired_token");
    localStorage.setItem("refresh_token", "my_refresh_token");

    const fetchSpy = jest.spyOn(global, "fetch")
      // First call: 401
      .mockResolvedValueOnce(jsonResponse({ detail: "Unauthorized" }, 401))
      // Refresh call: success
      .mockResolvedValueOnce(
        jsonResponse({
          access_token: "new_access",
          refresh_token: "new_refresh",
        }),
      )
      // Retry original call: success
      .mockResolvedValueOnce(jsonResponse({ data: "success" }));

    const { api } = await import("@/lib/api");

    const result = await api.get<{ data: string }>("/api/protected");

    // Should have made 3 fetch calls: original, refresh, retry
    expect(fetchSpy).toHaveBeenCalledTimes(3);

    // The refresh call goes to /api/auth/refresh
    const refreshCall = fetchSpy.mock.calls[1];
    expect(refreshCall[0]).toContain("/api/auth/refresh");

    // Final result should be from the retry
    expect(result).toEqual({ data: "success" });

    // Tokens should be updated in localStorage
    expect(localStorage.getItem("access_token")).toBe("new_access");
    expect(localStorage.getItem("refresh_token")).toBe("new_refresh");
  });

  it("throws ApiError when request fails and refresh is not available", async () => {
    localStorage.removeItem("refresh_token");
    localStorage.setItem("access_token", "bad_token");

    jest.spyOn(global, "fetch").mockResolvedValueOnce(
      jsonResponse({ detail: "Unauthorized" }, 401),
    );

    const { api, ApiError } = await import("@/lib/api");

    await expect(api.get("/api/protected")).rejects.toThrow(ApiError);
  });

  it("sends POST body as JSON", async () => {
    const fetchSpy = jest.spyOn(global, "fetch").mockResolvedValue(
      jsonResponse({ id: "123" }),
    );

    const { api } = await import("@/lib/api");

    await api.post("/api/items", { name: "test" });

    const [, options] = fetchSpy.mock.calls[0];
    expect((options as RequestInit).method).toBe("POST");
    expect((options as RequestInit).body).toBe(JSON.stringify({ name: "test" }));
  });
});
