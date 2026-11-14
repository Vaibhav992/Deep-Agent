import type { AgentEvent, RunMode } from "./types";

export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(message: string, public status: number) {
    super(message);
  }
}

type TokenGetter = () => Promise<string | null>;

async function request<T>(getToken: TokenGetter, path: string, init: RequestInit = {}): Promise<T> {
  const token = await getToken();
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      ...(init.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...init.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Request failed (${res.status})`, res.status);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  get: <T>(getToken: TokenGetter, path: string) => request<T>(getToken, path),
  post: <T>(getToken: TokenGetter, path: string, body: unknown) =>
    request<T>(getToken, path, { method: "POST", body: JSON.stringify(body) }),
  patch: <T>(getToken: TokenGetter, path: string, body: unknown) =>
    request<T>(getToken, path, { method: "PATCH", body: JSON.stringify(body) }),
  delete: (getToken: TokenGetter, path: string) => request<void>(getToken, path, { method: "DELETE" }),
};

export interface StreamRequest {
  sessionId: string;
  message: string;
  mode: RunMode;
  model?: string | null;
}

/**
 * POST /chat/stream and dispatch each SSE event.
 * Resolves when the stream ends; rejects on HTTP or network failure.
 * Aborting the signal closes the connection, which cancels the run server-side.
 */
export async function streamRun(
  getToken: TokenGetter,
  req: StreamRequest,
  onEvent: (ev: AgentEvent) => void,
  signal: AbortSignal,
): Promise<void> {
  const token = await getToken();
  const res = await fetch(`${API_URL}/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ session_id: req.sessionId, message: req.message, mode: req.mode, model: req.model ?? null }),
    signal,
  });
  if (!res.ok || !res.body) {
    const body = await res.json().catch(() => null);
    throw new ApiError(body?.detail ?? `Request failed (${res.status})`, res.status);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";
  let dataLines: string[] = [];

  const dispatch = () => {
    if (dataLines.length) {
      try {
        onEvent({ event: eventName, data: JSON.parse(dataLines.join("\n")) } as AgentEvent);
      } catch {
        // Ignore malformed frames; the server only sends JSON.
      }
    }
    eventName = "message";
    dataLines = [];
  };

  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.search(/\r?\n/)) >= 0) {
      const line = buffer.slice(0, nl);
      buffer = buffer.slice(nl + (buffer[nl] === "\r" ? 2 : 1));
      if (line === "") dispatch();
      else if (line.startsWith("event:")) eventName = line.slice(6).trim();
      else if (line.startsWith("data:")) dataLines.push(line.slice(5).replace(/^ /, ""));
      // Lines starting with ":" are keep-alive comments.
    }
  }
  dispatch();
}
