const API_URL = (import.meta.env.VITE_API_BASE_URL ?? "").trim().replace(/\/+$/, "");
const TOKEN_KEY = "cs2-open-case-token";
const ADMIN_TOKEN_KEY = "cs2-open-case-admin-token";

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  return sessionStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  sessionStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  sessionStorage.removeItem(TOKEN_KEY);
}

export function getAdminToken(): string | null {
  return sessionStorage.getItem(ADMIN_TOKEN_KEY);
}

export function setAdminToken(token: string): void {
  sessionStorage.setItem(ADMIN_TOKEN_KEY, token);
}

export function clearAdminToken(): void {
  sessionStorage.removeItem(ADMIN_TOKEN_KEY);
}

export async function api<T>(path: string, options: RequestInit = {}, authToken?: string | null): Promise<T> {
  if (import.meta.env.PROD && !API_URL) {
    throw new ApiError("Backend URL is not configured. Set VITE_API_BASE_URL in the frontend Vercel project.", 0);
  }

  const headers = new Headers(options.headers);
  headers.set("Content-Type", "application/json");
  const token = authToken === undefined ? getToken() : authToken;
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let response: Response;
  try {
    response = await fetch(`${API_URL}/api${path}`, { ...options, headers });
  } catch (error) {
    if (error instanceof TypeError) {
      throw new ApiError("Could not reach the backend. Check its deployment and the VITE_API_BASE_URL setting.", 0);
    }
    throw error;
  }

  if (!response.headers.get("content-type")?.includes("application/json")) {
    throw new ApiError(
      "The backend returned a non-JSON response. Check that VITE_API_BASE_URL points to the FastAPI deployment.",
      response.status,
    );
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null) as { detail?: string } | null;
    throw new ApiError(body?.detail ?? `Request failed (${response.status})`, response.status);
  }
  return response.json() as Promise<T>;
}
