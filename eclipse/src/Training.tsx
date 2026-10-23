import { useEffect, useState } from "react";
import { get, post } from "./api";

const SOURCES: [string, string][] = [
  ["traces", "Your successful chats: request, tool calls, real results, answer"],
  ["fixes", "Your chats where a broken build got fixed"],
  ["drills", "Correct tool habits: read before edit, rebuild after every change"],
  ["honesty", "Say plainly when something failed; never claim work that did not pass"],
  ["typos", "Your requests with spelling mistakes, mapped to the same actions"],
  ["spelling", "Fixing spelling in files without changing the meaning"],
  ["reading", "Answering from a file by quoting it, not guessing"],
  ["web", "Web search, reading pages and citing the link (real searches, done now)"],
  ["memory", "Your saved preferences"],
  ["media", "3D models, materials, animation, renders (Blender) and video editing (ffmpeg), each script run and kept only if it works"],
  ["cpp", "C and C++: thousands of public examples (Magicoder MIT, CodeFeedback Apache-2.0)"],
  ["skills", "The built-in how-to guides as questions and answers"],
  ["code", "Files from your own project folders, to learn your style"],
];

export function Training({ setModel }: { setModel: (m: string) => void }) {
  const [s, setS] = useState<any>(null);
  const [opts, setOpts] = useState<any>(null);
  const [folders, setFolders] = useState("");
  const load = async () => {
    const d = await get("/api/train").catch(() => null);
    setS(d);
    if (d && !opts) setOpts(d.defaults);
  };
  useEffect(() => { load(); }, []);
  useEffect(() => {
    if (s?.state !== "running") return;
    const id = setInterval(load, 2000);
    return () => clearInterval(id);
  }, [s?.state]);
  if (!s || !opts) return <div className="view"><div className="page muted">Loading…</div></div>;
  const running = s.state === "running";
  const plan = s.settings?.method ? s.settings : s.plan;
  const pct = s.total ? Math.floor((100 * s.step) / s.total) : 0;
  const start = async () => {
    await post("/api/train/start", { opts: { ...opts, code_folders: folders.split("\n").map((x) => x.trim()).filter(Boolean) } });
    load();
  };
  return (
    <div className="view"><div className="page">
      <h2>Training</h2>
      <div className="muted">Teaches qwen-abliterated your way of working. The result is added as a NEW model, qwen-abliterated-tuned; the original is never changed. Nothing leaves this machine except the public C++ download and the web searches you switch on.</div>
      {!s.tools_ready && <div className="card warn">{s.tools_why}</div>}
      <div className="card">
        <b>What goes in</b> <span className="muted">({s.your_turns} of your chat turns recorded so far)</span>
        {SOURCES.map(([k, label]) => (
          <label key={k} className="trow">
            <input type="checkbox" disabled={running} checked={!!opts[k]} onChange={(e) => setOpts({ ...opts, [k]: e.target.checked })} />
            <span><b>{k}</b> <span className="muted">{label}</span></span>
          </label>
        ))}
        {opts.code && (
          <textarea className="field mono" rows={3} style={{ width: "100%", marginTop: 6 }} disabled={running}
            placeholder={"One project folder per line, e.g.\nC:\\Users\\you\\Projects\\MyGame"} value={folders} onChange={(e) => setFolders(e.target.value)} />
        )}
        <div className="muted small" style={{ marginTop: 6 }}>Always removed: anything that looks like a password, key, token or email address; denied actions; turns that ended broken.</div>
      </div>
      <div className="card">
        <b>Settings (picked automatically)</b>
        {plan.ok === false && !running ? <div className="warn">{plan.why}</div> : (
          <div className="muted mono small">
            {plan.method === "mlx" ? "MLX LoRA (Apple Silicon)" : "Unsloth QLoRA 4-bit (NVIDIA)"}; base {plan.base}; {plan.max_seq_len} tokens per example;
            batch {plan.batch} x {plan.grad_accum}; {plan.epochs} epochs; learning rate {plan.lr}; LoRA rank {plan.lora_r}. Out of memory = retried smaller automatically.
          </div>
        )}
      </div>
      <div className="row">
        <button className="btn" disabled={running || !s.tools_ready || plan.ok === false} onClick={start}>Start training</button>
        {running && <button className="ghost danger" onClick={async () => { await post("/api/train/stop"); load(); }}>Stop</button>}
        <span className="muted">{running ? `${s.phase}…` : s.state === "done" ? "Finished" : s.state === "error" ? "" : ""}</span>
      </div>
      {(running || s.step > 0) && (
        <div className="card">
          <div className="setupbar"><span className="track" style={{ width: 260 }}><i style={{ width: pct + "%" }} /></span>
            <span className="mono">step {s.step} / {s.total || "?"}</span>
            {s.loss != null && <span className="mono muted">loss {Number(s.loss).toFixed(3)}</span>}
            {s.eval_loss != null && <span className="mono muted">held-out {Number(s.eval_loss).toFixed(3)}</span>}
          </div>
        </div>
      )}
      {s.result?.n > 0 && (
        <div className="card">
          <b>Result</b> on {s.result.n} held-out tasks: original <span className="mono">{s.result.old_score}%</span>, tuned <span className="mono">{s.result.new_score}%</span>.
          {s.result.better
            ? <> <button className="btn" onClick={() => setModel(s.result.new)}>Use the tuned model</button></>
            : <span className="muted"> The tuned model is not better, so keep the original.</span>}
        </div>
      )}
      {s.error && <div className="card warn">{s.error}</div>}
      {s.log?.length > 0 && <pre className="card mono small" style={{ maxHeight: 260, overflow: "auto", whiteSpace: "pre-wrap" }}>{s.log.join("\n")}</pre>}
    </div></div>
  );
}
