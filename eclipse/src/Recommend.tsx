import { useEffect, useState } from "react";
import { get, post } from "./api";

type M = { name: string; gb: number; need_gb: number; fit: string; good_for: string; tools: boolean; thinks: boolean; installed: boolean };
type R = { usable_gb: number; abliterated: M[]; regular: M[]; abliterated_pick: string; regular_pick: string };

const FIT: Record<string, string> = { fits: "Fits", tight: "Tight (spills to RAM, slower)", "too big": "Too big here" };

export function Recommend({ setModel }: { setModel: (m: string) => void }) {
  const [r, setR] = useState<R | null>(null);
  const [kind, setKind] = useState<"abliterated" | "regular">("abliterated");
  const [showAll, setShowAll] = useState(false);
  const [busy, setBusy] = useState("");
  const load = () => get("/api/recommend").then(setR).catch(() => setR(null));
  useEffect(() => { load(); }, []);

  async function pull(name: string) {
    setBusy(name);
    await post("/api/models/pull", { model: name }).catch(() => {});
    setBusy("");
    load();
  }

  if (!r) return <div className="view"><div className="page muted">Checking this machine…</div></div>;
  const list = r[kind].filter((m) => showAll || m.fit !== "too big");
  const pick = kind === "abliterated" ? r.abliterated_pick : r.regular_pick;
  return (
    <div className="view"><div className="page">
      <h2>Recommended models</h2>
      <div className="muted">{r.usable_gb} GB available for a model on this machine. Sizes include room for a 16k-token chat.</div>
      <div className="row" style={{ margin: "12px 0" }}>
        <div className="seg">
          <button className={kind === "abliterated" ? "on" : ""} onClick={() => setKind("abliterated")}>Abliterated</button>
          <button className={kind === "regular" ? "on" : ""} onClick={() => setKind("regular")}>Regular</button>
        </div>
        <label className="muted"><input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} /> Show models too big for this machine</label>
      </div>
      <div className="muted" style={{ marginBottom: 8 }}>
        {kind === "abliterated"
          ? "Refusals removed from the weights. Same skills as the originals, answers anything you ask."
          : "The official releases, unchanged."}
        {pick && <> Best fit with tool use: <span className="mono">{pick}</span>.</>}
      </div>
      <table className="table">
        <thead><tr><th>Model</th><th>Good for</th><th>Download</th><th>Needs</th><th>On this machine</th><th></th></tr></thead>
        <tbody>{list.map((m) => (
          <tr key={m.name}>
            <td className="mono">{m.name}{m.name === pick && <span className="okc"> best fit</span>}</td>
            <td>{m.good_for}{!m.tools && <span className="muted"> (chat only, no tools)</span>}{m.thinks && <span className="muted"> (thinks)</span>}</td>
            <td className="num">{m.gb} GB</td>
            <td className="num">{m.need_gb} GB</td>
            <td className={m.fit === "fits" ? "okc" : m.fit === "too big" ? "warn" : ""}>{FIT[m.fit]}</td>
            <td>{m.installed
              ? <button className="ghost" onClick={() => setModel(m.name)}>Use</button>
              : <button className="btn" disabled={!!busy || m.fit === "too big"} onClick={() => pull(m.name)}>{busy === m.name ? "Downloading…" : "Download"}</button>}</td>
          </tr>))}
        </tbody>
      </table>
    </div></div>
  );
}
