// Talks to the Python core (sidecar) over 127.0.0.1. Inside Tauri the Rust side tells us
// the port it started the core on; in a plain browser (dev/e2e) it is 5173.
const H = { "Content-Type": "application/json", "X-NC": "1" };
// Served by the core itself (desktop window) -> same origin. Vite dev server (:1420) -> :5173.
let base = location.port === "1420" ? "http://127.0.0.1:5173" : "";

export async function initCore(): Promise<string> {
  const w = window as unknown as { __TAURI_INTERNALS__?: unknown };
  if (w.__TAURI_INTERNALS__) {
    const { invoke } = await import("@tauri-apps/api/core");
    const port = await invoke<number>("core_port");
    base = `http://127.0.0.1:${port}`;
  }
  return base;
}

export async function get<T = any>(path: string): Promise<T> {
  const r = await fetch(base + path);
  return r.json();
}

export async function post<T = any>(path: string, body: unknown = {}): Promise<T> {
  const init = { method: "POST", headers: H, body: JSON.stringify(body) };
  const r = await fetch(base + path, init);
  return r.json();
}

export type Ev = { event: string; data: any };

// POST and read Server-Sent Events, calling onEvent for each one (awaited, so an
// approval card can pause the stream until the user answers).
export async function stream(path: string, body: unknown, onEvent: (e: Ev) => Promise<void> | void) {
  const init = { method: "POST", headers: H, body: JSON.stringify(body) };
  const res = await fetch(base + path, init);
  if (!res.body) throw new Error("no response body");
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = "";
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += dec.decode(value, { stream: true });
    const blocks = buf.split("\n\n");
    buf = blocks.pop() ?? "";
    for (const b of blocks) {
      const ev = /event: (.*)/.exec(b)?.[1];
      const raw = /data: (.*)/s.exec(b)?.[1];
      if (ev) await onEvent({ event: ev, data: raw ? JSON.parse(raw) : null });
    }
  }
}
