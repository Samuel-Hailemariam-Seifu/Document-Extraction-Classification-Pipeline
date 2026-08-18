import type { DocumentRecord, DocumentSummary, DocumentUpdate } from "./types";

/** Server-side: talk to FastAPI directly. Browser: same-origin via Next rewrites. */
function apiBase(): string {
  if (typeof window === "undefined") {
    return (
      process.env.BACKEND_URL ??
      process.env.NEXT_PUBLIC_API_URL ??
      "http://localhost:8000"
    );
  }
  return "";
}

export type ApiErrorBody = {
  message: string;
  code?: string;
  reset_hint?: string;
};

export async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json();
    const detail = body?.detail;
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && typeof detail.message === "string") {
      return detail.message;
    }
    if (typeof body?.message === "string") return body.message;
    return JSON.stringify(body);
  } catch {
    return res.statusText || "Request failed";
  }
}

export interface RateLimitStatus {
  limit_requests: number | null;
  remaining_requests: number | null;
  reset_requests: string | null;
  limit_tokens: number | null;
  remaining_tokens: number | null;
  reset_tokens: string | null;
  updated_at: string | null;
}

export const RATE_LIMIT_REFRESH_EVENT = "ratelimit-refresh";

export function notifyRateLimitRefresh() {
  if (typeof window !== "undefined") {
    window.dispatchEvent(new Event(RATE_LIMIT_REFRESH_EVENT));
  }
}

export async function getRateLimitStatus(): Promise<RateLimitStatus> {
  const res = await fetch(`${apiBase()}/api/status/rate-limit`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

/**
 * Browser-facing asset URLs must be same-origin (Next rewrites → FastAPI).
 * Always relative so SSR and client HTML match (avoids hydration mismatch).
 */
export function documentFileUrl(documentId: string): string {
  return `/api/documents/${documentId}/file`;
}

/** Rasterized first-page PNG for the review panel. */
export function documentPreviewUrl(documentId: string): string {
  return `/api/documents/${documentId}/preview`;
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${apiBase()}/api/documents/upload`, {
    method: "POST",
    body: form,
  });

  notifyRateLimitRefresh();

  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function listDocuments(): Promise<DocumentSummary[]> {
  const res = await fetch(`${apiBase()}/api/documents`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function getDocument(id: string): Promise<DocumentRecord> {
  const res = await fetch(`${apiBase()}/api/documents/${id}`, { cache: "no-store" });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}

export async function updateDocument(
  id: string,
  payload: DocumentUpdate,
): Promise<DocumentRecord> {
  const res = await fetch(`${apiBase()}/api/documents/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json();
}
