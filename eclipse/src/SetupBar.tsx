import { useEffect, useState } from "react";
import { get } from "./api";

// The core downloads qwen-abliterated in a background thread; this only polls and draws.
export function SetupBar() {
  const [s, setS] = useState<any>(null);
  useEffect(() => {
    let stop = false;
    const tick = async () => {
      const d = await get("/api/setup").catch(() => null);
      if (stop) return;
      setS(d);
      if (d && !["ready", "error", "idle"].includes(d.state)) setTimeout(tick, 1500);
    };
    tick();
    return () => { stop = true; };
  }, []);
  if (!s || s.state === "ready" || s.state === "idle") return null;
  if (s.state === "error") return <span className="warn">{s.error}</span>;
  const pct = s.total ? Math.floor((100 * s.completed) / s.total) : 0;
  return (
    <span className="setupbar" title={s.status}>
      {s.state === "pulling" ? "Downloading qwen-abliterated" : "Setting up qwen-abliterated"}
      {s.total ? <><span className="track"><i style={{ width: pct + "%" }} /></span>{pct}% of {(s.total / 2 ** 30).toFixed(1)} GB</> : ` ${s.status}`}
    </span>
  );
}
