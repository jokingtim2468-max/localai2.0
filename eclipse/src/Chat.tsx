import { useEffect, useRef, useState } from "react";
import { get, post, stream } from "./api";
import { Working } from "./Working";

type Item =
  | { kind: "user" | "assistant" | "sys"; text: string }
  | { kind: "tool"; name: string; args: any; result?: string }
  | { kind: "think"; text: string; secs?: number }
  | { kind: "approval"; id: string; tool: string; args: any; answer?: boolean };

type Msg = { role: string; content: string };

// /commands run in the app, never in the model.
const SLASH = ["/context", "/model", "/tools", "/clear"];

export function Chat({ model, setModel, log }: { model: string; setModel: (m: string) => void; log: (s: string) => void }) {
  const [items, setItems] = useState<Item[]>([]);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [label, setLabel] = useState("");
  const [tools, setTools] = useState(true);
  const [auto, setAuto] = useState(false);
  const end = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  const answer = useRef<((v: boolean) => void) | null>(null);

  useEffect(() => { if (pinned.current) end.current?.scrollIntoView({ behavior: "smooth" }); }, [items, busy]);
  const add = (it: Item) => setItems((xs) => [...xs, it]);
  const patchLast = (kind: Item["kind"], fn: (it: any) => any) =>
    setItems((xs) => {
      for (let i = xs.length - 1; i >= 0; i--) if (xs[i].kind === kind) {
        const c = xs.slice(); c[i] = fn({ ...xs[i] }); return c;
      }
      return xs;
    });

  async function slash(cmd: string, arg: string) {
    if (cmd === "/clear") { setItems([]); setMsgs([]); return; }
    if (cmd === "/tools") { setTools((t) => !t); add({ kind: "sys", text: `tools ${tools ? "off" : "on"}` }); return; }
    if (cmd === "/model") {
      if (arg) { setModel(arg); add({ kind: "sys", text: `model: ${arg}` }); return; }
      const d = await get("/api/models");
      add({ kind: "sys", text: "models: " + (d.models.map((m: any) => m.name).join(", ") || d.error || "none") });
      return;
    }
    if (cmd === "/context") {
      const st = await get("/api/settings");
      const chars = msgs.reduce((n, m) => n + m.content.length, 0);
      const toks = Math.round(chars / 3.5);
      add({ kind: "sys", text: `context: ~${toks} of ${st.num_ctx} tokens (${Math.round((100 * toks) / st.num_ctx)}%) in ${msgs.length} messages. Older turns are summarised automatically when it fills.` });
      return;
    }
    add({ kind: "sys", text: `unknown command ${cmd}. Try ${SLASH.join(" ")}` });
  }

  async function onEvent(e: { event: string; data: any }, reply: { text: string }) {
    const d = e.data;
    if (e.event === "thinking") {
      setItems((xs) => {
        const last = xs[xs.length - 1];
        if (last && last.kind === "think" && last.secs === undefined) return [...xs.slice(0, -1), { ...last, text: last.text + d }];
        return [...xs, { kind: "think", text: d }];
      });
    } else if (e.event === "token") {
      reply.text += d;
      setItems((xs) => {
        const c = xs.map((x) => (x.kind === "think" && x.secs === undefined ? { ...x, secs: 1 } : x));
        const last = c[c.length - 1];
        if (last && last.kind === "assistant") return [...c.slice(0, -1), { kind: "assistant", text: last.text + d }];
        return [...c, { kind: "assistant", text: d }];
      });
    }
    else if (e.event === "tool_call") {
      setLabel(`running ${d.name}…`);
      add({ kind: "tool", name: d.name, args: d.args });
      log(`tool ${d.name} ${JSON.stringify(d.args).slice(0, 120)}`);
    } else if (e.event === "tool_result") {
      setLabel("");
      patchLast("tool", (t) => ({ ...t, result: String(d.result) }));
      log(`  -> ${String(d.result).split("\n")[0].slice(0, 120)}`);
    } else if (e.event === "notice") {
      add({ kind: "sys", text: d });
    } else if (e.event === "error") {
      add({ kind: "sys", text: "error: " + d });
    }
    else if (e.event === "approval") {
      add({ kind: "approval", id: d.id, tool: d.tool, args: d.args });
      const ok = await new Promise<boolean>((res) => { answer.current = res; });
      answer.current = null;
      await post("/api/approve", { id: d.id, allow: ok });
      patchLast("approval", (a) => ({ ...a, answer: ok }));
    }
  }

  async function submit() {
    const line = text.trim();
    if (line === "" || busy) return;
    setText("");
    if (line.startsWith("/")) {
      const [cmd, ...rest] = line.split(" ");
      await slash(cmd, rest.join(" "));
      return;
    }
    const history = [...msgs, { role: "user", content: line }];
    setMsgs(history);
    add({ kind: "user", text: line });
    setBusy(true);
    const reply = { text: "" };
    const body = { model, messages: history, tools, ask: !auto };
    try {
      await stream("/api/chat", body, (e) => onEvent(e, reply));
    } catch (err) {
      add({ kind: "sys", text: "core unreachable: " + String(err) });
    }
    setItems((xs) => xs.map((x) => (x.kind === "think" && x.secs === undefined ? { ...x, secs: 1 } : x)));
    if (reply.text) setMsgs((m) => [...m, { role: "assistant", content: reply.text }]);
    setBusy(false);
    setLabel("");
  }

  const isErr = (r?: string) => !!r && /^\s*(error|FAILED|blocked)/.test(r);
  const empty = items.length === 0;
  return (
    <div className="chatpane">
    <div className="view" onScroll={(ev) => {
      const el = ev.currentTarget;
      pinned.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    }}>
      <div className="chat">
        {empty && (
          <div className="card">
            <b>Point Eclipse at a folder and tell it what to build.</b>
            <div className="muted">It writes files there, runs the build, reads the errors and fixes them. Commands ask first unless Auto is on. Type / for app commands.</div>
          </div>
        )}
        {items.map((it, i) => {
          if (it.kind === "tool") return (
            <div key={i} className="tool">
              <div>{it.name} <span className="muted">{JSON.stringify(it.args).slice(0, 140)}</span></div>
              {it.result !== undefined && <pre className={isErr(it.result) ? "err" : "ok"}>{it.result.slice(0, 4000)}</pre>}
            </div>
          );
          if (it.kind === "think") return (
            <details key={i} className="think" open={it.secs === undefined}>
              <summary>{it.secs === undefined ? "Thinking…" : "Thought"}</summary>
              <div>{it.text}</div>
            </details>
          );
          if (it.kind === "approval") return (
            <div key={i} className="approval">
              <b>Allow {it.tool}?</b>
              <pre>{JSON.stringify(it.args, null, 1)}</pre>
              {it.answer === undefined ? (
                <div className="row">
                  <button className="btn" onClick={() => answer.current?.(true)}>Allow</button>
                  <button className="ghost" onClick={() => answer.current?.(false)}>Deny</button>
                </div>
              ) : <span className="muted">{it.answer ? "allowed" : "denied"}</span>}
            </div>
          );
          return <div key={i} className={"msg " + it.kind}>{it.text}</div>;
        })}
        {busy && <Working label={label} />}
        <div ref={end} />
      </div>
    </div>
    <div className="composer">
      <div className="box">
        <textarea value={text} rows={1} placeholder="Build, fix, run… or /context /model /tools /clear"
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} />
        <div className="row">
          <span className="muted mono">{model || "no model"}</span>
          <button className={"ghost" + (tools ? " on" : "")} onClick={() => setTools(!tools)}>Tools {tools ? "on" : "off"}</button>
          <button className={"ghost" + (auto ? " on" : "")} onClick={() => setAuto(!auto)} title="run commands without asking">Auto {auto ? "on" : "off"}</button>
          <span style={{ flex: 1 }} />
          <button className="btn" disabled={busy || !text.trim()} onClick={submit}>Send</button>
        </div>
      </div>
    </div>
    </div>
  );
}
