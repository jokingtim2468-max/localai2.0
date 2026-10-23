import { useEffect, useState } from "react";
import { get, post } from "./api";

export function Settings() {
  const [s, setS] = useState<any>(null);
  const [keySet, setKeySet] = useState(false);
  const [key, setKey] = useState("");
  const [keyNote, setKeyNote] = useState("");
  useEffect(() => {
    get("/api/settings").then(setS).catch(() => setS({ error: true }));
    get("/api/web/key").then((d) => setKeySet(d.set)).catch(() => {});
  }, []);
  const saveKey = async (k: string) => {
    const r = await post("/api/web/key", { key: k });
    setKeyNote(r.ok ? (k ? "Saved in the system keychain." : "Removed.") : r.error);
    setKeySet(!!k && r.ok); setKey("");
  };
  const save = async (k: string, v: any) => setS(await post("/api/settings", { [k]: v }));
  if (!s) return <div className="view"><div className="page muted">Loading…</div></div>;
  if (s.error) return <div className="view"><div className="page warn">The Eclipse core is not running.</div></div>;
  return (
    <div className="view"><div className="page">
      <h2>Settings</h2>
      <div className="card">
        <label>Model server <select className="field" value={s.backend} onChange={(e) => save("backend", e.target.value)}>
          <option value="ollama">Ollama</option><option value="llamacpp">llama.cpp server</option><option value="mlx">MLX (Apple Silicon)</option>
        </select></label>{" "}
        <input className="field mono" placeholder="default address" defaultValue={s.backend_url} onBlur={(e) => save("backend_url", e.target.value)} />
      </div>
      <div className="card">
        <label><input type="checkbox" checked={!!s.web} onChange={(e) => save("web", e.target.checked)} /> Web: let the agent search the web and read pages</label>
        <div className="muted">Uses Ollama's web search when an Ollama API key is saved (free at ollama.com/settings/keys), otherwise a plain DuckDuckGo search. Local and private addresses are always blocked.</div>
        <div className="row" style={{ marginTop: 8 }}>
          <input className="field mono" type="password" placeholder={keySet ? "Ollama API key saved" : "Ollama API key (optional)"} value={key} onChange={(e) => setKey(e.target.value)} />
          <button className="btn" disabled={!key} onClick={() => saveKey(key)}>Save key</button>
          {keySet && <button className="ghost" onClick={() => saveKey("")}>Remove</button>}
          <span className="muted">{keyNote}</span>
        </div>
      </div>
      <div className="card">
        <label>Context length <input className="field mono" type="number" defaultValue={s.num_ctx} onBlur={(e) => save("num_ctx", +e.target.value)} /></label>
        <div className="muted">Bigger remembers more of the chat but uses more memory. 16384 suits 8 GB GPUs.</div>
      </div>
      <div className="card">
        <label>Project folder <input className="field mono" style={{ width: "100%" }} placeholder="default: Eclipse data folder/workspace" defaultValue={s.workdir} onBlur={(e) => save("workdir", e.target.value)} /></label>
        <label><input type="checkbox" checked={s.trust_workspace} onChange={(e) => save("trust_workspace", e.target.checked)} /> Edit and delete files in the project folder without asking (commands still ask)</label><br />
        <label><input type="checkbox" checked={s.think} onChange={(e) => save("think", e.target.checked)} /> Let thinking models reason before answering (slower)</label>
      </div>
    </div></div>
  );
}
