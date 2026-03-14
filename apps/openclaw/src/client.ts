/**
 * Typed HTTP client for the OC Logistics backend API.
 *
 * Config is read from environment variables:
 *   OC_BACKEND_URL   — base URL, e.g. http://localhost:8000
 *   OC_BACKEND_TOKEN — JWT bearer token (owner or dispatcher)
 */

export function getBackendConfig(): { baseUrl: string; token: string } {
  const baseUrl = process.env.OC_BACKEND_URL?.replace(/\/$/, "") ?? "http://localhost:8000";
  const token = process.env.OC_BACKEND_TOKEN ?? "";
  return { baseUrl, token };
}

export class BackendError extends Error {
  constructor(
    readonly status: number,
    readonly detail: string,
  ) {
    super(`Backend ${status}: ${detail}`);
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
): Promise<T> {
  const { baseUrl, token } = getBackendConfig();
  const url = `${baseUrl}${path}`;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const resp = await fetch(url, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const err = (await resp.json()) as { detail?: string };
      if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
    } catch {
      // ignore parse errors
    }
    throw new BackendError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json() as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body: unknown) => request<T>("POST", path, body),
  patch: <T>(path: string, body: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
};

// ── Result helpers ────────────────────────────────────────────────────────────

export type ToolContent = { type: "text"; text: string };

export function ok(data: unknown): { content: ToolContent[]; details: unknown } {
  return {
    content: [{ type: "text", text: JSON.stringify(data, null, 2) }],
    details: data,
  };
}

export function err(e: unknown): { content: ToolContent[]; details: unknown } {
  const msg = e instanceof Error ? e.message : String(e);
  return {
    content: [{ type: "text", text: `Error: ${msg}` }],
    details: { error: msg },
  };
}
