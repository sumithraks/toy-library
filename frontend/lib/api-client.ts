const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000/api";

export class ApiError extends Error {
  status: number;
  body: unknown;

  constructor(status: number, body: unknown) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? String((body as { detail: unknown }).detail)
        : `Request failed with status ${status}`;
    super(detail);
    this.status = status;
    this.body = body;
  }
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem("toy_library_token");
}

export function setToken(token: string | null) {
  if (typeof window === "undefined") return;
  if (token) {
    window.localStorage.setItem("toy_library_token", token);
  } else {
    window.localStorage.removeItem("toy_library_token");
  }
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  auth?: boolean;
};

export async function apiFetch<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = "GET", body, auth = true } = options;
  const headers: Record<string, string> = { "Content-Type": "application/json" };

  if (auth) {
    const token = getToken();
    if (token) headers["Authorization"] = `Token ${token}`;
  }

  const res = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const data = text ? JSON.parse(text) : undefined;

  if (!res.ok) {
    throw new ApiError(res.status, data);
  }
  return data as T;
}
