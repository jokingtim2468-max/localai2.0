import { useEffect, useRef, useState } from "react";

export type Cmd = { label: string; hint?: string; run: () => void };

// Ctrl/Cmd+K. Arrow keys move, Enter runs, Esc closes.
export function Palette({ cmds, close }: { cmds: Cmd[]; close: () => void }) {
  const [q, setQ] = useState("");
  const [sel, setSel] = useState(0);
  const box = useRef<HTMLDivElement>(null);
  const hits = cmds.filter((c) => c.label.toLowerCase().includes(q.toLowerCase()));
  useEffect(() => {
    box.current?.animate([{ opacity: 0, transform: "translateY(-6px) scale(.98)" }, { opacity: 1, transform: "none" }],
      { duration: 150, easing: "ease-out" });
  }, []);
  const key = (e: React.KeyboardEvent) => {
    if (e.key === "Escape") close();
    else if (e.key === "ArrowDown") { e.preventDefault(); setSel((s) => Math.min(s + 1, hits.length - 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setSel((s) => Math.max(s - 1, 0)); }
    else if (e.key === "Enter" && hits[sel]) { hits[sel].run(); close(); }
  };
  return (
    <div className="palette-bg" onMouseDown={close}>
      <div className="palette" ref={box} onMouseDown={(e) => e.stopPropagation()}>
        <input autoFocus placeholder="Type a command" value={q} onKeyDown={key} onChange={(e) => { setQ(e.target.value); setSel(0); }} />
        <ul>{hits.map((c, i) => (
          <li key={c.label} className={i === sel ? "on" : ""} onMouseEnter={() => setSel(i)} onClick={() => { c.run(); close(); }}>
            <span>{c.label}</span><span className="muted mono">{c.hint}</span>
          </li>))}
        </ul>
      </div>
    </div>
  );
}
