import type { ApiError } from "./types";

export class HmApiError extends Error {
  code: string;
  status: number;
  constructor(status: number, body: ApiError) {
    super(body.message);
    this.code = body.error_code;
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!r.ok) {
    const body = (await r.json().catch(() => ({ error_code: "Unknown", message: r.statusText }))) as ApiError;
    throw new HmApiError(r.status, body);
  }
  if (r.status === 204) return undefined as T;
  return (await r.json()) as T;
}

export const api = {
  get: <T,>(p: string) => request<T>(p),
  post: <T,>(p: string, body?: unknown) =>
    request<T>(p, { method: "POST", body: JSON.stringify(body ?? {}) }),
  put: <T,>(p: string, body?: unknown) =>
    request<T>(p, { method: "PUT", body: JSON.stringify(body ?? {}) }),
};
