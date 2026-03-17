/**
 * HTTP client wrapper for the kandidat REST API.
 * All MCP tools call the API through this single client.
 */

const API_URL = (process.env.KANDIDAT_API_URL || "http://localhost:8000").replace(
  /\/$/,
  ""
);

const TIMEOUT_MS = 30_000;

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly body: string
  ) {
    super(`API error ${status}: ${body}`);
    this.name = "ApiError";
  }
}

interface RequestOptions {
  method?: string;
  body?: unknown;
  params?: Record<string, string>;
  timeout?: number;
}

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<T> {
  const { method = "GET", body, params, timeout = TIMEOUT_MS } = options;

  let url = `${API_URL}${path}`;
  if (params) {
    const searchParams = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value) searchParams.set(key, value);
    }
    const qs = searchParams.toString();
    if (qs) url += `?${qs}`;
  }

  const headers: Record<string, string> = {};
  let fetchBody: string | undefined;

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    fetchBody = JSON.stringify(body);
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      method,
      headers,
      body: fetchBody,
      signal: controller.signal,
    });

    const text = await response.text();

    if (!response.ok) {
      throw new ApiError(response.status, text);
    }

    return JSON.parse(text) as T;
  } finally {
    clearTimeout(timer);
  }
}

// Typed response envelope from kandidat API
interface ApiResponse<T> {
  data: T;
}

interface ApiErrorResponse {
  error: string;
}

/**
 * GET request to kandidat API. Returns the `data` field from the response.
 */
export async function apiGet<T>(
  path: string,
  params?: Record<string, string>
): Promise<T> {
  const response = await request<ApiResponse<T>>(path, { params });
  return response.data;
}

/**
 * POST request to kandidat API. Returns the `data` field from the response.
 */
export async function apiPost<T>(path: string, body?: unknown): Promise<T> {
  const response = await request<ApiResponse<T>>(path, {
    method: "POST",
    body,
  });
  return response.data;
}

/**
 * PUT request to kandidat API. Returns the `data` field from the response.
 */
export async function apiPut<T>(path: string, body: unknown): Promise<T> {
  const response = await request<ApiResponse<T>>(path, {
    method: "PUT",
    body,
  });
  return response.data;
}

/**
 * PATCH request to kandidat API. Returns the `data` field from the response.
 */
export async function apiPatch<T>(path: string, body: unknown): Promise<T> {
  const response = await request<ApiResponse<T>>(path, {
    method: "PATCH",
    body,
  });
  return response.data;
}

/**
 * DELETE request to kandidat API. Returns the `data` field from the response.
 */
export async function apiDelete<T>(path: string): Promise<T> {
  const response = await request<ApiResponse<T>>(path, { method: "DELETE" });
  return response.data;
}
