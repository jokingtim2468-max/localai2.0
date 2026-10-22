import { useEffect, useState } from "react";
import { get, post } from "./api";

export function Settings() {
  const [s, setS] = useState<any>(null);
  useEffect(() => { get("/api/settings").then(setS).catch(() => setS({ error: true })); }, []);
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
