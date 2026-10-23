import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
import { GLTFExporter } from "three/examples/jsm/exporters/GLTFExporter.js";
import { base, get, post, stream } from "./api";

// 3D model studio. Left-click a part (no drag) = select it and edit its properties on the right.
// Drag a part = move it (in the plane facing the camera). Drag empty space = orbit, wheel = zoom.
// Right-click a part = leave a comment / ask the model to change that part.
type Sel = { uuid: string; name: string };
type Menu = { x: number; y: number; uuid: string; name: string; point: number[] };

const DRAG_PX = 4;

export function Studio({ model }: { model: string }) {
  const wrap = useRef<HTMLDivElement>(null);
  const three = useRef<{ scene: THREE.Scene; cam: THREE.PerspectiveCamera; ren: THREE.WebGLRenderer; ctl: OrbitControls; root?: THREE.Object3D } | null>(null);
  const [files, setFiles] = useState<{ path: string; size: number }[]>([]);
  const [file, setFile] = useState("");
  const [sel, setSel] = useState<Sel | null>(null);
  const [tick, setTick] = useState(0);              // re-render the props panel after edits
  const [menu, setMenu] = useState<Menu | null>(null);
  const [ask, setAsk] = useState("");
  const [log, setLog] = useState("");
  const [busy, setBusy] = useState("");
  const [dirty, setDirty] = useState(false);
  const [comments, setComments] = useState<any[]>([]);

  const listFiles = () => get("/api/model3d/list").then((d) => setFiles(d.models || [])).catch(() => {});
  useEffect(() => { listFiles(); }, []);

  // ---------- three.js setup ----------
  useEffect(() => {
    const el = wrap.current!;
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x111111);
    const cam = new THREE.PerspectiveCamera(45, 1, 0.01, 2000);
    cam.position.set(1.5, 1.2, 2);
    const ren = new THREE.WebGLRenderer({ antialias: true });
    ren.setPixelRatio(devicePixelRatio);
    el.appendChild(ren.domElement);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x333333, 1.2));
    const sun = new THREE.DirectionalLight(0xffffff, 2); sun.position.set(3, 5, 4); scene.add(sun);
    scene.add(new THREE.GridHelper(10, 40, 0x333333, 0x222222));
    const ctl = new OrbitControls(cam, ren.domElement);
    ctl.enableDamping = true;
    three.current = { scene, cam, ren, ctl };
    const size = () => { const r = el.getBoundingClientRect(); ren.setSize(r.width, r.height); cam.aspect = r.width / Math.max(1, r.height); cam.updateProjectionMatrix(); };
    size();
    const ro = new ResizeObserver(size); ro.observe(el);
    let raf = 0;
    const loop = () => { ctl.update(); ren.render(scene, cam); raf = requestAnimationFrame(loop); };
    loop();
    return () => { cancelAnimationFrame(raf); ro.disconnect(); ren.dispose(); el.removeChild(ren.domElement); };
  }, []);

  // ---------- load a model ----------
  const load = async (path: string) => {
    const t = three.current; if (!t || !path) return;
    setBusy("loading " + path); setSel(null); setMenu(null);
    if (t.root) { t.scene.remove(t.root); t.root = undefined; }
    try {
      const g = await new GLTFLoader().loadAsync(`${base()}/api/model3d/file?path=${encodeURIComponent(path)}&t=${Date.now()}`);
      t.root = g.scene; t.scene.add(g.scene);
      const box = new THREE.Box3().setFromObject(g.scene);
      const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3()).length() || 1;
      t.ctl.target.copy(c); t.cam.position.copy(c).add(new THREE.Vector3(s * 0.8, s * 0.5, s * 0.9)); t.cam.near = s / 500; t.cam.far = s * 50; t.cam.updateProjectionMatrix();
      setDirty(false);
      post("/api/model3d/comments", { path }).then((d) => setComments(d.comments || []));
    } catch (e) { setLog("could not load: " + e); }
    setBusy("");
  };
  useEffect(() => { load(file); }, [file]);

  const find = (uuid: string) => three.current?.root?.getObjectByProperty("uuid", uuid) as THREE.Mesh | undefined;

  // ---------- pick / drag ----------
  const ray = new THREE.Raycaster();
  const pick = (ev: { clientX: number; clientY: number }) => {
    const t = three.current; if (!t?.root) return null;
    const r = t.ren.domElement.getBoundingClientRect();
    const p = new THREE.Vector2(((ev.clientX - r.left) / r.width) * 2 - 1, -((ev.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(p, t.cam);
    return ray.intersectObject(t.root, true).find((h) => (h.object as THREE.Mesh).isMesh) || null;
  };

  const onDown = (ev: React.PointerEvent) => {
    if (ev.button !== 0) return;
    const t = three.current!; setMenu(null);
    const hit = pick(ev);
    if (!hit) return;                                   // empty space: OrbitControls orbits
    t.ctl.enabled = false;
    const obj = hit.object;
    const plane = new THREE.Plane().setFromNormalAndCoplanarPoint(t.cam.getWorldDirection(new THREE.Vector3()), hit.point);
    const startWorld = obj.getWorldPosition(new THREE.Vector3());
    const grab = hit.point.clone();
    const x0 = ev.clientX, y0 = ev.clientY;
    let dragging = false;
    const move = (e: PointerEvent) => {
      if (!dragging && Math.hypot(e.clientX - x0, e.clientY - y0) < DRAG_PX) return;
      dragging = true;
      const r = t.ren.domElement.getBoundingClientRect();
      ray.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), t.cam);
      const at = new THREE.Vector3();
      if (!ray.ray.intersectPlane(plane, at)) return;
      const world = startWorld.clone().add(at.sub(grab));
      obj.position.copy(obj.parent ? obj.parent.worldToLocal(world) : world);
      setDirty(true);
    };
    const up = () => {
      removeEventListener("pointermove", move); removeEventListener("pointerup", up);
      t.ctl.enabled = true;
      setSel({ uuid: obj.uuid, name: obj.name || "(unnamed)" });     // click and drag both select it
      setTick((k) => k + 1);
    };
    addEventListener("pointermove", move); addEventListener("pointerup", up);
  };

  const onContext = (ev: React.MouseEvent) => {
    ev.preventDefault();
    const hit = pick(ev);
    if (!hit) { setMenu(null); return; }
    setSel({ uuid: hit.object.uuid, name: hit.object.name || "(unnamed)" });
    setMenu({ x: ev.clientX, y: ev.clientY, uuid: hit.object.uuid, name: hit.object.name || "(unnamed)", point: hit.point.toArray().map((v) => +v.toFixed(4)) });
    setAsk("");
  };

  // ---------- edit selected part ----------
  const obj = sel ? find(sel.uuid) : undefined;
  const mat = obj && (Array.isArray(obj.material) ? obj.material[0] : obj.material) as THREE.MeshStandardMaterial | undefined;
  const setVec = (key: "position" | "scale", i: number, v: number) => { if (!obj || isNaN(v)) return; obj[key].setComponent(i, v); setDirty(true); setTick((k) => k + 1); };
  const setRot = (i: number, deg: number) => { if (!obj || isNaN(deg)) return; const r = obj.rotation.toArray(); r[i] = (deg * Math.PI) / 180; obj.rotation.set(r[0] as number, r[1] as number, r[2] as number); setDirty(true); setTick((k) => k + 1); };
  const num = (v: number) => +v.toFixed(4);

  // ---------- save ----------
  const save = async () => {
    const t = three.current; if (!t?.root || !file) return;
    setBusy("saving");
    const buf = await new GLTFExporter().parseAsync(t.root, { binary: true }) as ArrayBuffer;
    let s = ""; const u = new Uint8Array(buf);
    for (let i = 0; i < u.length; i += 0x8000) s += String.fromCharCode(...u.subarray(i, i + 0x8000));
    const r = await post("/api/model3d/save", { path: file, b64: btoa(s) });
    setLog(r.error ? "save failed: " + r.error : `saved ${file} (${r.bytes} bytes, previous kept as .bak)`);
    if (!r.error) setDirty(false);
    setBusy("");
  };

  // ---------- right-click: comment / ask the model ----------
  const comment = async (send: boolean) => {
    if (!menu || !ask.trim()) return;
    const m = menu; setMenu(null);
    const d = await post("/api/model3d/comment", { path: file, part: m.name, text: ask, point: m.point });
    setComments(d.comments || []);
    if (!send) { setLog(`comment saved on ${m.name}`); return; }
    const o = find(m.uuid);
    const info = o ? { position: o.position.toArray().map(num), point: m.point } : { point: m.point };
    const { prompt } = await post("/api/model3d/prompt", { path: file, part: m.name, text: ask, info });
    await runAgent(prompt, "model is working on " + m.name);
    load(file);                                         // pick up the edited model
  };

  // the chat agent (qwen-abliterated by default) does the Blender work; its output streams into the side panel
  const runAgent = async (prompt: string, label: string) => {
    setBusy(label); setLog("");
    let out = "";
    try {
      await stream("/api/chat", { model, messages: [{ role: "user", content: prompt }], tools: true, ask: true }, async (e) => {
        if (e.event === "token") { out += e.data; setLog(out); }
        else if (e.event === "tool_call") { out += `\n▸ ${e.data.name}\n`; setLog(out); }
        else if (e.event === "tool_result") { out += String(e.data.result).slice(0, 600) + "\n"; setLog(out); }
        else if (e.event === "approval") {
          const ok = confirm(`Allow ${e.data.tool}?\n\n${JSON.stringify(e.data.args, null, 1).slice(0, 800)}`);
          await post("/api/approve", { id: e.data.id, allow: ok });
        } else if (e.event === "error") { out += "\nerror: " + e.data; setLog(out); }
      });
    } catch (x) { setLog(out + "\nerror: " + x); }
    setBusy("");
  };

  // ---------- make a brand-new model from a description ----------
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const create = async () => {
    if (!newDesc.trim()) return;
    const r = await post("/api/model3d/create", { name: newName || newDesc.split(" ").slice(0, 3).join("_"), desc: newDesc });
    if (r.error) { setLog(r.error); return; }
    await runAgent(r.prompt, "model is building " + r.path);
    await listFiles();
    setFile(""); setTimeout(() => setFile(r.path), 0);
  };

  return (
    <div className="studio">
      <div className="b-bar">
        <select className="field" value={file} onChange={(e) => { if (dirty && !confirm("Discard unsaved changes?")) return; setFile(e.target.value); }}>
          <option value="">Open a model…</option>
          {files.map((f) => <option key={f.path} value={f.path}>{f.path}</option>)}
        </select>
        <button className="ghost" onClick={listFiles}>Refresh</button>
        <button className="ghost" onClick={() => load(file)} disabled={!file}>Reload</button>
        <button onClick={save} disabled={!file || !dirty}>Save</button>
        <input className="field" style={{ width: 120 }} placeholder="name" value={newName} onChange={(e) => setNewName(e.target.value)} />
        <input className="field" style={{ flex: 1, minWidth: 200 }} placeholder="Describe a new model, e.g. a dented metal trash can, 0.9 m tall" value={newDesc}
          onChange={(e) => setNewDesc(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") create(); }} />
        <button onClick={create} disabled={!newDesc.trim() || !!busy}>Make model</button>
      </div>
      <div className="b-bar">
        <span className="muted small">Click a part to edit · drag a part to move it · drag empty space to orbit · right-click a part to tell the model</span>
      </div>
      <div className="s-body">
        <div className="s-view" ref={wrap} onPointerDown={onDown} onContextMenu={onContext} />
        <aside className="b-props" data-tick={tick}>
          {!obj && <p className="muted small">{file ? "Click a part of the model." : "Pick a .glb from your workspace."}</p>}
          {obj && (
            <>
              <h3>{sel!.name}</h3>
              <label>Name<input className="field" value={obj.name} onChange={(e) => { obj.name = e.target.value; setSel({ ...sel!, name: e.target.value }); setDirty(true); }} /></label>
              {(["position", "scale"] as const).map((k) => (
                <label key={k}>{k}<div className="row3">{[0, 1, 2].map((i) => (
                  <input key={i} className="field mono" type="number" step={k === "scale" ? 0.05 : 0.01} value={num(obj[k].getComponent(i))} onChange={(e) => setVec(k, i, parseFloat(e.target.value))} />))}</div></label>
              ))}
              <label>rotation °<div className="row3">{[0, 1, 2].map((i) => (
                <input key={i} className="field mono" type="number" step={5} value={num(((obj.rotation.toArray()[i] as number) * 180) / Math.PI)} onChange={(e) => setRot(i, parseFloat(e.target.value))} />))}</div></label>
              {mat?.color && <label>colour<input type="color" value={"#" + mat.color.getHexString()} onChange={(e) => { mat.color.set(e.target.value); setDirty(true); setTick((k) => k + 1); }} /></label>}
              {mat && "roughness" in mat && <label>roughness<input type="range" min={0} max={1} step={0.01} value={mat.roughness} onChange={(e) => { mat.roughness = +e.target.value; setDirty(true); setTick((k) => k + 1); }} /></label>}
              {mat && "metalness" in mat && <label>metal<input type="range" min={0} max={1} step={0.01} value={mat.metalness} onChange={(e) => { mat.metalness = +e.target.value; setDirty(true); setTick((k) => k + 1); }} /></label>}
              <label className="chk"><input type="checkbox" checked={obj.visible} onChange={(e) => { obj.visible = e.target.checked; setDirty(true); setTick((k) => k + 1); }} /> visible</label>
              <button className="ghost" onClick={() => { obj.parent?.remove(obj); setSel(null); setDirty(true); }}>Delete part</button>
            </>
          )}
          {!!comments.length && <><h3>Comments</h3>{comments.slice(-8).map((c, i) => <p key={i} className="small"><b>{c.part}</b>: {c.text}</p>)}</>}
          {log && <pre className="s-log">{log}</pre>}
        </aside>
      </div>
      {menu && (
        <div className="b-menu" style={{ left: menu.x, top: menu.y }} onPointerDown={(e) => e.stopPropagation()}>
          <b>{menu.name}</b>
          <textarea className="field" autoFocus rows={3} placeholder="What should change on this part?" value={ask} onChange={(e) => setAsk(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) comment(true); if (e.key === "Escape") setMenu(null); }} />
          <div className="row">
            <button onClick={() => comment(true)} disabled={!ask.trim()}>Ask model</button>
            <button className="ghost" onClick={() => comment(false)} disabled={!ask.trim()}>Just comment</button>
          </div>
        </div>
      )}
      {busy && <div className="b-busy">{busy}</div>}
    </div>
  );
}
