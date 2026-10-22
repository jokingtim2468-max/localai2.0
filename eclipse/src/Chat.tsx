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
