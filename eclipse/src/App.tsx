import { useEffect, useState } from "react";
import { get, initCore, post } from "./api";
import { Chat } from "./Chat";
import { Icon } from "./icons";
import { Models } from "./Models";
import { Cmd, Palette } from "./Palette";
import { Planned } from "./Planned";
import { Settings } from "./Settings";

const SCREENS: [string, string][] = [
  ["chat", "Chat"], ["projects", "Projects"], ["models", "Models"], ["game", "Game kit"],
  ["gui", "GUI builder"], ["shield", "Anti-tamper lab"], ["bench", "Analysis bench"],
  ["fork", "Open-source adapter"], ["assets", "Assets"],
];

export function App() {
  const [tabs, setTabs] = useState<string[]>(["chat"]);
  const [on, setOn] = useState("chat");
  const [model, setModel] = useState("");
  const [core, setCore] = useState<"wait" | "ok" | "down">("wait");
  const [logs, setLogs] = useState<string[]>([]);
  const [drawer, setDrawer] = useState(false);
  const [inspector, setInspector] = useState(true);
  const [palette, setPalette] = useState(false);
  const [hw, setHw] = useState<any>(null);
  const log = (s: string) => setLogs((l) => [...l.slice(-300), new Date().toLocaleTimeString() + "  " + s]);

  useEffect(() => {
    (async () => {
      await initCore().catch(() => {});
      try {
        await get("/api/health");
        setCore("ok");
        log("core ready");
        const m = await get("/api/models");
        const st = await get("/api/settings");
        setModel(st.model || m.models?.[0]?.name || "");
        if (m.error) log(m.error);
        get("/api/hardware").then(setHw).catch(() => {});
      } catch {
        setCore("down");
        log("core not reachable on 127.0.0.1");
      }
    })();
  }, []);

  useEffect(() => {
    const k = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setPalette((p) => !p); }
      if ((e.metaKey || e.ctrlKey) && e.key === "`") { e.preventDefault(); setDrawer((d) => !d); }
    };
    addEventListener("keydown", k);
    return () => removeEventListener("keydown", k);
  }, []);

  const open = (id: string) => { setTabs((t) => (t.includes(id) ? t : [...t, id])); setOn(id); };
  const closeTab = (id: string) => {
    const rest = tabs.filter((t) => t !== id);
    setTabs(rest.length ? rest : ["chat"]);
    if (on === id) setOn(rest[rest.length - 1] || "chat");
  };

  const stopAll = async () => {
    const r = await post("/api/models/stop").catch((e) => ({ error: String(e) }));
    log(r.error ? "stop failed: " + r.error : `stopped ${r.stopped} model(s)`);
  };
  const title = (id: string) => (id === "settings" ? "Settings" : SCREENS.find((s) => s[0] === id)?.[1] || id);
  const cmds: Cmd[] = [
    ...SCREENS.map(([id, name]) => ({ label: "Open " + name, run: () => open(id) })),
    { label: "Open Settings", run: () => open("settings") },
    { label: "Toggle terminal and logs", hint: "Ctrl+`", run: () => setDrawer((d) => !d) },
    { label: "Toggle inspector", run: () => setInspector((i) => !i) },
    { label: "Stop all models", run: stopAll },
  ];

  const page = (id: string) =>
    id === "chat" ? <Chat model={model} setModel={setModel} log={log} />
      : id === "models" ? <Models model={model} setModel={(m) => { setModel(m); post("/api/settings", { model: m }); }} />
      : id === "settings" ? <Settings />
      : <Planned id={id} />;

  return (
    <div className="shell" style={{ gridTemplateColumns: `48px 1fr ${inspector ? "280px" : "0px"}` }}>
      <nav className="rail">
        {SCREENS.map(([id, name]) => (
          <button key={id} title={name} aria-label={name} className={on === id ? "on" : ""} onClick={() => open(id)}><Icon name={id} /></button>
        ))}
        <span className="grow" />
        <button title="Settings" aria-label="Settings" className={on === "settings" ? "on" : ""} onClick={() => open("settings")}><Icon name="settings" /></button>
      </nav>
      <section className="center">
        <div className="tabs">
          {tabs.map((id) => (
            <div key={id} className={"tab" + (on === id ? " on" : "")} onClick={() => setOn(id)}>
              {title(id)}
              {tabs.length > 1 && <span className="x" onClick={(e) => { e.stopPropagation(); closeTab(id); }}>×</span>}
            </div>
          ))}
        </div>
        {tabs.map((id) => (
          <div key={id} style={{ display: on === id ? "flex" : "none", flex: 1, minHeight: 0, flexDirection: "column" }}>{page(id)}</div>
        ))}
      </section>
      <aside className="inspector" style={{ display: inspector ? "block" : "none" }}>
        <h3>This machine</h3>
        {hw ? (
          <div className="muted">
            <div className="mono">{hw.info.cpu || hw.info.arch}</div>
            <div>{hw.info.ram_gb ?? "?"} GB memory, {hw.recommend.usable_gb} GB for models</div>
            {hw.recommend.warning && <div className="warn">{hw.recommend.warning}</div>}
          </div>
        ) : <div className="muted">Checking…</div>}
        <h3 style={{ marginTop: 16 }}>Model</h3>
        <div className="mono">{model || "none picked"}</div>
        <button className="ghost" style={{ marginTop: 8 }} onClick={() => open("models")}>Manage models</button>
      </aside>
      {drawer && (
        <div className="drawer">
          <div className="tabs"><div className="tab on">Logs</div></div>
          <pre>{logs.join("\n") || "Nothing yet."}</pre>
        </div>
      )}
      <footer className="status">
        <span><span className={"dot " + (core === "ok" ? "ok" : core === "down" ? "bad" : "")} />core {core === "ok" ? "running" : core === "down" ? "offline" : "starting"}</span>
        <span>{model || "no model"}</span>
        <span className="grow" />
        <button onClick={() => setDrawer((d) => !d)}>logs</button>
        <button onClick={stopAll}>stop all models</button>
        <button onClick={() => setPalette(true)}>Ctrl+K</button>
      </footer>
      {palette && <Palette cmds={cmds} close={() => setPalette(false)} />}
    </div>
  );
}
