import { useEffect, useRef, useState } from "react";
import { post } from "./api";

// Builder: the model drafts a screen, you edit it by hand.
// Left-click selects (drag to move, corner to resize, double-click to edit text).
// Right-click opens a menu to tell the model what to change about that element.
type El = { id: string; type: string; x: number; y: number; w: number; h: number; text: string; style: any; options?: string[] };

const W = 1200, H = 800, GRID = 8;
const snap = (n: number) => Math.round(n / GRID) * GRID;
const uid = () => Math.random().toString(36).slice(2, 8);
const PALETTE: [string, string, Partial<El>][] = [
  ["heading", "Heading", { w: 400, h: 48, text: "Heading", style: { size: 32, weight: 600 } }],
  ["text", "Text", { w: 320, h: 48, text: "Some text" }],
  ["button", "Button", { w: 140, h: 40, text: "Button" }],
  ["input", "Text box", { w: 280, h: 40, text: "Type here…" }],
  ["textarea", "Big text box", { w: 360, h: 120, text: "Write here…" }],
  ["checkbox", "Checkbox", { w: 200, h: 28, text: "Option" }],
  ["select", "Dropdown", { w: 220, h: 40, text: "", options: ["Option 1", "Option 2"] }],
  ["image", "Image", { w: 240, h: 160, text: "" }],
  ["box", "Box / panel", { w: 400, h: 240, text: "", style: { bg: "#121212", radius: 10 } }],
  ["divider", "Divider", { w: 400, h: 2, text: "" }],
];

export function Builder() {
  const [doc, setDoc] = useState<El[]>([]);
  const [sel, setSel] = useState<string>("");
  const [editing, setEditing] = useState("");
  const [menu, setMenu] = useState<{ x: number; y: number; id: string } | null>(null);
  const [ask, setAsk] = useState("");
  const [prompt, setPrompt] = useState("");
  const [name, setName] = useState("screen");
  const [busy, setBusy] = useState("");
  const [note, setNote] = useState("");
  const [scale, setScale] = useState(0.7);
  const history = useRef<El[][]>([]);
  const wrap = useRef<HTMLDivElement>(null);
  const cur = doc.find((e) => e.id === sel);

  // every change goes through here so Ctrl+Z works
  const commit = (next: El[]) => { history.current = [...history.current.slice(-50), doc]; setDoc(next); };
  const patch = (id: string, p: Partial<El>) => commit(doc.map((e) => (e.id === id ? { ...e, ...p } : e)));
  const patchStyle = (id: string, k: string, v: any) => {
    const e = doc.find((x) => x.id === id);
    if (e) patch(id, { style: { ...e.style, [k]: v } });
  };
  const undo = () => { const prev = history.current.pop(); if (prev) setDoc(prev); };
  const remove = (id: string) => { commit(doc.filter((e) => e.id !== id)); setSel(""); };
  const duplicate = (id: string) => {
    const e = doc.find((x) => x.id === id);
    if (!e) return;
    const c = { ...e, id: uid(), x: Math.min(W - e.w, e.x + 16), y: Math.min(H - e.h, e.y + 16) };
    commit([...doc, c]); setSel(c.id);
  };
  const add = (type: string, base: Partial<El>) => {
    const e: El = { id: uid(), type, x: 80, y: 80, w: 200, h: 40, text: "", style: {}, ...base } as El;
    commit([...doc, e]); setSel(e.id);
  };
  const toFront = (id: string) => { const e = doc.find((x) => x.id === id); if (e) commit([...doc.filter((x) => x.id !== id), e]); };
  const toBack = (id: string) => { const e = doc.find((x) => x.id === id); if (e) commit([e, ...doc.filter((x) => x.id !== id)]); };

  // fit the 1200x800 canvas into the available space
  useEffect(() => {
    const fit = () => {
      const r = wrap.current?.getBoundingClientRect();
      if (r && r.width > 0) setScale(Math.max(0.3, Math.min(1, (r.width - 32) / W, (r.height - 32) / H)));
    };
    const ro = new ResizeObserver(fit);       // also fires when the tab becomes visible
    if (wrap.current) ro.observe(wrap.current);
    return () => ro.disconnect();
  }, []);

  // drag to move / resize; one history entry per drag
  function startDrag(ev: React.PointerEvent, e: El, mode: "move" | "size") {
    if (ev.button !== 0 || editing === e.id) return;
    ev.stopPropagation();
    setSel(e.id); setMenu(null);
    history.current = [...history.current.slice(-50), doc];
    const sx = ev.clientX, sy = ev.clientY, o = { ...e };
    const move = (m: PointerEvent) => {
      const dx = (m.clientX - sx) / scale, dy = (m.clientY - sy) / scale;
      setDoc((d) => d.map((x) => x.id !== e.id ? x : mode === "move"
        ? { ...x, x: Math.max(0, Math.min(W - x.w, snap(o.x + dx))), y: Math.max(0, Math.min(H - x.h, snap(o.y + dy))) }
        : { ...x, w: Math.max(GRID, Math.min(W - x.x, snap(o.w + dx))), h: Math.max(2, Math.min(H - x.y, snap(o.h + dy))) }));
    };
    const up = () => { removeEventListener("pointermove", move); removeEventListener("pointerup", up); };
    addEventListener("pointermove", move); addEventListener("pointerup", up);
  }

  async function generate() {
    if (!prompt.trim()) return;
    setBusy("Drafting the layout…"); setNote("");
    const r = await post("/api/builder/generate", { prompt }).catch((e) => ({ error: String(e) }));
    setBusy("");
    if (r.error) { setNote("Could not draft it: " + r.error); return; }
    commit(r.elements); setSel("");
    setNote(`${r.elements.length} elements. Click one to edit it, right-click to ask for a change.`);
  }

  async function askModel() {
    const e = doc.find((x) => x.id === menu?.id);
    if (!e || !ask.trim()) return;
    setMenu(null); setBusy(`Updating ${e.type}…`);
    const r = await post("/api/builder/edit", { element: e, doc, instruction: ask }).catch((x) => ({ error: String(x) }));
    setBusy(""); setAsk("");
    if (r.error) { setNote("The model could not change it: " + r.error); return; }
    patch(e.id, r.element); setSel(e.id);
  }

  async function save() {
    const r = await post("/api/builder/save", { name, doc }).catch((e) => ({ error: String(e) }));
    setNote(r.error ? "Save failed: " + r.error : `Saved to the workspace: ${r.path} (and .json to reopen it)`);
  }

  useEffect(() => {
    const k = (ev: KeyboardEvent) => {
      const typing = (ev.target as HTMLElement)?.closest?.("input,textarea,select,[contenteditable=true]");
      if (typing || !wrap.current?.offsetParent) return;      // ignore keys while this tab is hidden
      if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") { ev.preventDefault(); undo(); return; }
      if (!sel) return;
      const e = doc.find((x) => x.id === sel);
      if (!e) return;
      const step = ev.shiftKey ? GRID * 4 : GRID;
      if (ev.key === "Delete" || ev.key === "Backspace") { ev.preventDefault(); remove(sel); }
      else if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "d") { ev.preventDefault(); duplicate(sel); }
      else if (ev.key === "ArrowLeft") patch(sel, { x: Math.max(0, e.x - step) });
      else if (ev.key === "ArrowRight") patch(sel, { x: Math.min(W - e.w, e.x + step) });
      else if (ev.key === "ArrowUp") patch(sel, { y: Math.max(0, e.y - step) });
      else if (ev.key === "ArrowDown") patch(sel, { y: Math.min(H - e.h, e.y + step) });
      else if (ev.key === "Escape") { setSel(""); setMenu(null); }
    };
    addEventListener("keydown", k);
    return () => removeEventListener("keydown", k);
  });

  // what each element looks like on the canvas (matches the HTML export)
  function look(e: El) {
    const s = e.style || {};
    const css: React.CSSProperties = {
      color: s.color, background: s.bg, fontSize: s.size, fontWeight: s.weight, textAlign: s.align,
      borderRadius: s.radius,
    };
    const text = editing === e.id ? undefined : e.text;
    if (e.type === "image") return <div className="b-img" style={css}>{e.text ? <img src={e.text} alt="" /> : "Image"}</div>;
    if (e.type === "divider") return <div className="b-div" />;
    if (e.type === "checkbox") return <label className="b-check" style={css}><input type="checkbox" readOnly /> <span>{text}</span></label>;
    if (e.type === "select") return <div className="b-field b-select" style={css}>{(e.options || [])[0] || "Choose…"} <span className="muted">▾</span></div>;
    if (e.type === "input" || e.type === "textarea") return <div className={"b-field" + (e.type === "textarea" ? " tall" : "")} style={css}><span className="muted">{text}</span></div>;
    if (e.type === "button") return <div className={"b-btn" + (s.bg === "#FF6D00" ? " primary" : "")} style={css}>{text}</div>;
    return <div className={"b-text " + e.type} style={css}>{text}</div>;
  }

  return (
    <div className="builder" onClick={() => setMenu(null)}>
      <div className="b-top">
        <input className="field grow" placeholder="Describe a screen: a login page with email, password and a sign-in button" value={prompt}
          onChange={(e) => setPrompt(e.target.value)} onKeyDown={(e) => e.key === "Enter" && generate()} />
        <button className="btn" disabled={!!busy || !prompt.trim()} onClick={generate}>Draft it</button>
        <span className="sep" />
        <input className="field mono" style={{ width: 140 }} value={name} onChange={(e) => setName(e.target.value)} title="file name" />
        <button className="ghost" onClick={save} disabled={!doc.length}>Save as HTML</button>
        <button className="ghost" onClick={undo} title="Ctrl+Z">Undo</button>
        <button className="ghost" onClick={() => { if (doc.length && confirm("Clear the canvas?")) { commit([]); setSel(""); } }}>Clear</button>
      </div>
      <div className="b-body">
        <aside className="b-palette">
          <h3>Add</h3>
          {PALETTE.map(([t, label, base]) => (
            <button key={t} className="b-add" onClick={() => add(t, base)}>{label}</button>
          ))}
          <p className="muted small">Click to edit. Drag to move, drag the corner to resize, double-click to change the text. Right-click to ask the model.</p>
        </aside>
        <div className="b-stage" ref={wrap} onPointerDown={() => { setSel(""); setEditing(""); }}>
          <div style={{ width: W * scale, height: H * scale }}>
          <div className="b-canvas" style={{ width: W, height: H, transform: `scale(${scale})` }}>
            {!doc.length && !busy && <div className="b-empty">Describe a screen above and the model drafts it here, or add pieces from the left.</div>}
            {doc.map((e) => (
              <div key={e.id} className={"b-el" + (e.id === sel ? " on" : "")}
                style={{ left: e.x, top: e.y, width: e.w, height: e.h }}
                onPointerDown={(ev) => startDrag(ev, e, "move")}
                onDoubleClick={(ev) => { ev.stopPropagation(); if (!["image", "divider", "select"].includes(e.type)) setEditing(e.id); }}
                onContextMenu={(ev) => { ev.preventDefault(); ev.stopPropagation(); setSel(e.id); setMenu({ x: ev.clientX, y: ev.clientY, id: e.id }); }}>
                {look(e)}
                {editing === e.id && (
                  <div className="b-edit" contentEditable suppressContentEditableWarning autoFocus
                    ref={(n) => { if (n && document.activeElement !== n) { n.focus(); document.getSelection()?.selectAllChildren(n); } }}
                    onPointerDown={(ev) => ev.stopPropagation()}
                    onBlur={(ev) => { patch(e.id, { text: ev.currentTarget.textContent || "" }); setEditing(""); }}
                    onKeyDown={(ev) => { if (ev.key === "Enter" && e.type !== "textarea") { ev.preventDefault(); (ev.target as HTMLElement).blur(); } }}>
                    {e.text}
                  </div>
                )}
                {e.id === sel && editing !== e.id && <span className="b-handle" onPointerDown={(ev) => startDrag(ev, e, "size")} />}
              </div>
            ))}
          </div>
          </div>
          {busy && <div className="b-busy">{busy}</div>}
        </div>
        <aside className="b-props">
          {cur ? (
            <>
              <h3>{PALETTE.find((p) => p[0] === cur.type)?.[1] || cur.type}</h3>
              {!["divider"].includes(cur.type) && (
                <label>{cur.type === "image" ? "Image URL or file path" : cur.type === "input" || cur.type === "textarea" ? "Placeholder" : "Text"}
                  {cur.type === "textarea" || cur.type === "text"
                    ? <textarea className="field" rows={3} value={cur.text} onChange={(e) => patch(cur.id, { text: e.target.value })} />
                    : <input className="field" value={cur.text} onChange={(e) => patch(cur.id, { text: e.target.value })} />}
                </label>
              )}
              {cur.type === "select" && (
                <label>Options (one per line)
                  <textarea className="field" rows={4} value={(cur.options || []).join("\n")} onChange={(e) => patch(cur.id, { options: e.target.value.split("\n") })} />
                </label>
              )}
              <div className="b-grid">
                {(["x", "y", "w", "h"] as const).map((k) => (
                  <label key={k}>{k.toUpperCase()}<input className="field mono" type="number" value={cur[k]}
                    onChange={(e) => patch(cur.id, { [k]: Math.max(0, +e.target.value) } as any)} /></label>
                ))}
              </div>
              <div className="b-grid">
                <label>Text colour<input type="color" value={cur.style?.color || "#E0E0E0"} onChange={(e) => patchStyle(cur.id, "color", e.target.value)} /></label>
                <label>Fill<input type="color" value={cur.style?.bg || "#121212"} onChange={(e) => patchStyle(cur.id, "bg", e.target.value)} /></label>
                <label>Size<input className="field mono" type="number" value={cur.style?.size || 14} onChange={(e) => patchStyle(cur.id, "size", +e.target.value)} /></label>
                <label>Corners<input className="field mono" type="number" value={cur.style?.radius ?? 6} onChange={(e) => patchStyle(cur.id, "radius", +e.target.value)} /></label>
              </div>
              <div className="row">
                <button className={"ghost" + (cur.style?.weight >= 600 ? " on" : "")} onClick={() => patchStyle(cur.id, "weight", cur.style?.weight >= 600 ? 400 : 600)}>Bold</button>
                {["left", "center", "right"].map((a) => (
                  <button key={a} className={"ghost" + (cur.style?.align === a ? " on" : "")} onClick={() => patchStyle(cur.id, "align", a)}>{a}</button>
                ))}
              </div>
              {cur.type === "button" && <button className="ghost" onClick={() => patchStyle(cur.id, "bg", cur.style?.bg === "#FF6D00" ? "" : "#FF6D00")}>{cur.style?.bg === "#FF6D00" ? "Make it a normal button" : "Make it the main button"}</button>}
              <div className="row">
                <button className="ghost" onClick={() => duplicate(cur.id)}>Duplicate</button>
                <button className="ghost" onClick={() => toFront(cur.id)}>To front</button>
                <button className="ghost" onClick={() => toBack(cur.id)}>To back</button>
                <button className="ghost danger" onClick={() => remove(cur.id)}>Delete</button>
              </div>
            </>
          ) : <p className="muted">Nothing selected. Click something on the canvas to edit it.</p>}
          {note && <p className="muted small">{note}</p>}
        </aside>
      </div>
      {menu && (
        <div className="b-menu" style={{ left: Math.min(menu.x, innerWidth - 300), top: Math.min(menu.y, innerHeight - 220) }}
          onClick={(e) => e.stopPropagation()} onPointerDown={(e) => e.stopPropagation()}>
          <div className="b-menu-ask">
            <input className="field" autoFocus placeholder="Tell the model what to change here…" value={ask}
              onChange={(e) => setAsk(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") askModel(); if (e.key === "Escape") setMenu(null); }} />
            <button className="btn" disabled={!ask.trim()} onClick={askModel}>Ask</button>
          </div>
          <button onClick={() => { setEditing(menu.id); setMenu(null); }}>Edit text</button>
          <button onClick={() => { duplicate(menu.id); setMenu(null); }}>Duplicate</button>
          <button onClick={() => { toFront(menu.id); setMenu(null); }}>Bring to front</button>
          <button className="danger" onClick={() => { remove(menu.id); setMenu(null); }}>Delete</button>
        </div>
      )}
    </div>
  );
}
