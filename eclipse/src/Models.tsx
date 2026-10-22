import { useEffect, useState } from "react";
import { get, post } from "./api";

type Model = { name: string; size: number; quant: string; params: string };
const gb = (b: number) => (b ? (b / 2 ** 30).toFixed(1) + " GB" : "-");

export function Models({ model, setModel }: { model: string; setModel: (m: string) => void }) {
  const [list, setList] = useState<Model[]>([]);
  const [err, setErr] = useState("");
  const [hw, setHw] = useState<any>(null);
  const [speed, setSpeed] = useState<Record<string, string>>({});
  const [pull, setPull] = useState("");

  async function refresh() {
    const d = await get("/api/models").catch(() => ({ models: [], error: "core offline" }));
    setList(d.models || []);
    setErr(d.error || "");
  }
  useEffect(() => { refresh(); get("/api/hardware").then(setHw).catch(() => {}); }, []);

  async function bench(name: string) {
    setSpeed((s) => ({ ...s, [name]: "measuring…" }));
    const r = await post("/api/models/bench", { model: name }).catch((e) => ({ error: String(e) }));
    setSpeed((s) => ({ ...s, [name]: r.error ? "failed" : `${r.tok_s} tok/s, first token ${r.first_token_s}s` }));
  }

  async function remove(name: string) {
    if (!confirm(`Delete ${name} from disk?`)) return;
    await post("/api/models/delete", { model: name });
    refresh();
  }

  const rec = hw?.recommend;
  const info = hw?.info;
  const power = hw?.power;
  const total = list.reduce((n, m) => n + (m.size || 0), 0);
  return (
    <div className="view"><div className="page">
      <h2>Models</h2>
      {info && (
        <div className="card">
          <div><b>{info.cpu || info.arch}</b>, {info.ram_gb ?? "?"} GB memory{info.gpu ? `, ${info.gpu}` : ""}{info.vram_gb && !info.apple_silicon ? ` (${info.vram_gb} GB VRAM)` : ""}</div>
          <div className="muted">Room for models: {rec.usable_gb} GB. Good fits here: <span className="mono">{rec.models.join(", ")}</span></div>
          {rec.warning && <div className="warn">{rec.warning}</div>}
          {power && <div className="muted">{power.plugged_in === false ? `On battery (${power.battery}%) — a smaller model will last longer` : "Plugged in"}{power.throttled ? ". " : ""}{power.throttled && <span className="warn">{power.note}</span>}</div>}
        </div>
      )}
      {err && <div className="card warn">{err}. Start Ollama (or switch backend in Settings), then refresh.</div>}
      <div className="row">
        <input className="field mono" placeholder="qwen2.5-coder:7b" value={pull} onChange={(e) => setPull(e.target.value)} />
        <button className="btn" disabled={!pull} onClick={async () => { await post("/api/models/pull", { model: pull }); setPull(""); refresh(); }}>Pull</button>
        <button className="ghost" onClick={refresh}>Refresh</button>
        <span className="muted">{list.length} installed, {gb(total)} on disk</span>
      </div>
      <table className="table">
        <thead><tr><th>Model</th><th>Size</th><th>Quant</th><th>Speed on this machine</th><th></th></tr></thead>
        <tbody>{list.map((m) => (
          <tr key={m.name}>
            <td className="mono">{m.name}{m.name === model && <span className="okc"> (in use)</span>}</td>
            <td className="num">{gb(m.size)}</td>
            <td className="num">{m.quant || "-"}</td>
            <td className="num">{speed[m.name] || <button className="ghost" onClick={() => bench(m.name)}>Measure</button>}</td>
            <td className="row">
              <button className="ghost" onClick={() => setModel(m.name)}>Use</button>
              <button className="ghost" onClick={() => remove(m.name)}>Delete</button>
            </td>
          </tr>))}
        </tbody>
      </table>
    </div></div>
  );
}
