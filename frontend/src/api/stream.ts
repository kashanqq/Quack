// Server-sent events over POST. The chat endpoints answer a POST with a `text/event-stream`, which
// EventSource cannot do, so the frames are read from a fetch body here.
//
// Frame shapes mirror backend/app/schemas/chat.py (StreamEvent). Keep in sync: the OpenAPI schema
// does not describe streaming bodies.

import { ApiError, request } from "./client";

export type StreamEvent =
  | { type: "text_delta"; text: string }
  | { type: "tool_call"; tool: string; args: Record<string, unknown>; call_id: string }
  | { type: "tool_result"; tool: string; call_id: string; data: unknown; error: string | null }
  | {
      type: "done";
      event_id: number;
      mode: string | null;
      gave_task_instance_id: string | null;
      hint_level: number | null;
      referenced_skill_ids: string[];
    }
  | { type: "error"; code: string; message: string };

/** Splits an SSE byte stream into `data:` payloads; comments (`: keepalive`) are dropped. */
export function createFrameParser(onData: (data: string) => void) {
  let buffer = "";
  return (chunk: string) => {
    buffer += chunk.replace(/\r\n/g, "\n");
    let end: number;
    while ((end = buffer.indexOf("\n\n")) !== -1) {
      const frame = buffer.slice(0, end);
      buffer = buffer.slice(end + 2);
      const data = frame
        .split("\n")
        .filter((line) => line.startsWith("data:"))
        .map((line) => line.slice(5).replace(/^ /, ""))
        .join("\n");
      if (data) onData(data);
    }
  };
}

/**
 * POSTs `body` and calls `onEvent` for each frame until `done` / `error` or the stream ends.
 * Failures before the stream starts (401, 503 `llm_unavailable`, 409 chat busy) reject with ApiError.
 * Abort through `signal`; an abort rejects with an AbortError.
 */
export async function postSSE(
  path: string,
  body: unknown,
  onEvent: (event: StreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  const res = await request("POST", path, body, { signal, headers: { Accept: "text/event-stream" } });
  if (!res.body) throw new ApiError(res.status, "internal", "Empty stream");

  let finished = false;
  const feed = createFrameParser((data) => {
    let event: StreamEvent;
    try {
      event = JSON.parse(data) as StreamEvent;
    } catch {
      return;
    }
    if (event.type === "done" || event.type === "error") finished = true;
    onEvent(event);
  });

  const reader = res.body.pipeThrough(new TextDecoderStream()).getReader();
  try {
    while (!finished) {
      const { value, done } = await reader.read();
      if (done) break;
      feed(value);
    }
  } finally {
    reader.cancel().catch(() => undefined);
  }
}
