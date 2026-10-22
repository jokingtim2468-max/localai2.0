// Night Crew web UI: chats (saved to chats.json via /api/chats), streaming chat with tool
// cards, approvals, a live "Thinking..." block and the orbit + shimmer working indicator.
const $ = (s) => document.querySelector(s);
const chat = $("#chat"), input = $("#input");
const state = { chats: [], cur: 0, busy: false, tools: true, auto: false };
const H = { "Content-Type": "application/json", "X-NC": "1" };
const esc = (s) => String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));

let pinned = true;
chat.addEventListener("scroll", () => { pinned = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80; });
function bottom(force) { if (force || pinned) chat.scrollTo({ top: chat.scrollHeight, behavior: "smooth" }); }

// ---------- chats ----------
const cur = () => state.chats[state.cur];
async function load() {
  try { const d = await (await fetch("/api/chats")).json(); state.chats = d.chats || []; } catch { state.chats = []; }
  if (!state.chats.length) state.chats.push({ title: "New chat", messages: [] });
  renderList(); renderThread();
}
function save() { fetch("/api/chats", { method: "POST", headers: H, body: JSON.stringify({ chats: state.chats }) }); }
function renderList() {
  $("#chats").innerHTML = state.chats.map((c, i) =>
    `<li data-i="${i}" class="${i === state.cur ? "on" : ""}">${esc(c.title)}</li>`).join("");
  $("#chats").querySelectorAll("li").forEach((li) => li.onclick = () => {
    if (state.busy) return; state.cur = +li.dataset.i; renderList(); renderThread(); });
}
function renderThread() {
  chat.innerHTML = "";
  for (const m of cur().messages) addMsg(m.role, m.content);
  bottom(true);
}
function addMsg(role, text) {
  const d = document.createElement("div"); d.className = "msg " + role; d.textContent = text;
  chat.appendChild(d); bottom(); return d;
}

// ---------- working indicator: orbit + shimmering words + timer ----------
const WORDS = ["Thinking", "Stargazing", "Charting a course", "Orbiting the problem", "Consulting the stars",
  "Pondering", "Plotting", "Mapping constellations", "Calibrating", "Reading the night sky"];
let orb = null, orbAnims = [], orbTimer = null, orbFixed = "";
function showOrbit() {
  orb = document.createElement("div"); orb.className = "orbit-wrap"; orb.setAttribute("role", "status");
  orb.innerHTML = `<span class="orbit"><span class="sun"></span><span class="arm"><span class="planet"></span></span></span>
    <span class="olabel shimmer"></span><span class="otime"></span>`;
  chat.appendChild(orb);
  // Web Animations, not CSS keyframes: Windows "animation effects off" freezes CSS spinners
  orbAnims = [orb.querySelector(".arm").animate([{ transform: "rotate(0)" }, { transform: "rotate(360deg)" }],
                { duration: 2600, iterations: Infinity }),
              orb.querySelector(".olabel").animate([{ backgroundPosition: "100% 0" }, { backgroundPosition: "-100% 0" }],
                { duration: 2000, iterations: Infinity })];
  const t0 = Date.now(); let i = Math.floor(Math.random() * WORDS.length), tick = 0;
  const paint = () => {
    if (!orb) return;
    orb.querySelector(".olabel").textContent = orbFixed || WORDS[i % WORDS.length] + "…";
    const s = Math.round((Date.now() - t0) / 1000);
    orb.querySelector(".otime").textContent = s >= 2 ? s + "s" : "";
  };
  paint(); orbTimer = setInterval(() => { if (++tick % 3 === 0) i++; paint(); }, 1000);
  bottom();
}
function orbitLabel(t) { orbFixed = t || ""; }
function orbitToEnd() { if (orb) chat.appendChild(orb); }
function hideOrbit() { orbAnims.forEach((a) => a.cancel()); clearInterval(orbTimer); orb?.remove(); orb = null; orbFixed = ""; }

// ---------- thinking block: live, then folded to "Thought for Ns" ----------
function thinkBlock() {
  const d = document.createElement("details"); d.className = "think"; d.open = true;
  d.innerHTML = `<summary class="shimmer">Thinking…</summary><div class="body"></div>`;
  chat.appendChild(d); orbitToEnd(); d.t0 = Date.now(); d.text = "";
  d.anim = d.querySelector("summary").animate([{ backgroundPosition: "100% 0" }, { backgroundPosition: "-100% 0" }],
    { duration: 2000, iterations: Infinity });
  return d;
}
function thinkDone(d) {
  if (!d || d.done) return; d.done = true; d.anim.cancel();
  const s = d.querySelector("summary"); s.classList.remove("shimmer");
  s.textContent = `Thought for ${Math.max(1, Math.round((Date.now() - d.t0) / 1000))}s`; d.open = false;
}

// ---------- tool cards + approvals ----------
function addTool(name, args) {
  const d = document.createElement("div"); d.className = "tool";
  d.innerHTML = `<div>▸ ${esc(name)} <span class="muted">${esc(JSON.stringify(args).slice(0, 160))}</span></div>`;
  chat.appendChild(d); orbitToEnd(); bottom(); return d;
}
function addResult(card, result) {
  const r = document.createElement("div");
  r.className = "res " + (/^\s*(error|FAILED|blocked)/.test(result) ? "err" : "ok");
  r.textContent = String(result).slice(0, 4000); card.appendChild(r); bottom();
}
function approval(data) {
  return new Promise((resolve) => {
    const d = document.createElement("div"); d.className = "approval";
    d.innerHTML = `<b>Allow ${esc(data.tool)}?</b><pre>${esc(JSON.stringify(data.args, null, 1))}</pre>
      <button class="btn" data-a="1">Allow</button><button class="chip" data-a="0">Deny</button>`;
    chat.appendChild(d); orbitToEnd(); bottom(true);
    d.querySelectorAll("button").forEach((b) => b.onclick = async () => {
      await fetch("/api/approve", { method: "POST", headers: H, body: JSON.stringify({ id: data.id, allow: b.dataset.a === "1" }) });
      d.innerHTML = `<span class="muted">${esc(data.tool)}: ${b.dataset.a === "1" ? "allowed" : "denied"}</span>`;
      resolve();
    });
  });
}

// ---------- send + stream ----------
async function send(text) {
  const c = cur();
  if (!c.messages.length) { c.title = text.slice(0, 40); renderList(); }
  c.messages.push({ role: "user", content: text }); addMsg("user", text); save();
  state.busy = true; $("#send").disabled = true; showOrbit();
  try { await stream(c); } catch (e) { addMsg("assistant", "error: " + e.message); }
  hideOrbit(); state.busy = false; $("#send").disabled = false; save();
}
async function stream(c) {
  const res = await fetch("/api/chat", { method: "POST", headers: H, body: JSON.stringify({
    model: $("#model").value, messages: c.messages, tools: state.tools, ask: !state.auto }) });
  const reader = res.body.getReader(), dec = new TextDecoder();
  let buf = "", body = null, acc = "", card = null, think = null;
  for (;;) {
    const { done, value } = await reader.read(); if (done) break;
    buf += dec.decode(value, { stream: true });
    const blocks = buf.split("\n\n"); buf = blocks.pop();
    for (const b of blocks) {
      const ev = /event: (.*)/.exec(b)?.[1], raw = /data: (.*)/s.exec(b)?.[1];
      if (!ev) continue; const data = raw ? JSON.parse(raw) : null;
      if (ev === "thinking") {
        if (!think || think.done) think = thinkBlock();
        think.text += data; think.querySelector(".body").textContent = think.text; bottom();
      } else if (ev === "token") {
        thinkDone(think);
        if (!body) { body = addMsg("assistant", ""); orbitToEnd(); }
        acc += data; body.textContent = acc; bottom();
      } else if (ev === "tool_call") {
        thinkDone(think); body = null; card = addTool(data.name, data.args); orbitLabel(`running ${data.name}…`);
      } else if (ev === "tool_result") {
        if (card) addResult(card, data.result); card = null; orbitLabel("");
      } else if (ev === "approval") { await approval(data); }
      else if (ev === "notice") { const n = addMsg("notice", "(" + data + ")"); n.className = "notice"; }
      else if (ev === "error") { addMsg("assistant", "error: " + data); }
      else if (ev === "done") { thinkDone(think); }
    }
  }
  if (acc) c.messages.push({ role: "assistant", content: acc });
}

// ---------- wiring ----------
$("#composer").onsubmit = (e) => { e.preventDefault(); const t = input.value.trim();
  if (!t || state.busy) return; input.value = ""; input.style.height = "auto"; send(t); };
input.addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); $("#composer").requestSubmit(); } });
input.addEventListener("input", () => { input.style.height = "auto"; input.style.height = input.scrollHeight + "px"; });
$("#new").onclick = () => { if (state.busy) return; state.chats.unshift({ title: "New chat", messages: [] });
  state.cur = 0; renderList(); renderThread(); save(); };
$("#tools").onclick = (e) => { state.tools = !state.tools; e.target.classList.toggle("on", state.tools); };
$("#auto").onclick = (e) => { state.auto = !state.auto; e.target.classList.toggle("on", state.auto); };
(async () => {
  load();
  try {
    const d = await (await fetch("/api/models")).json();
    $("#model").innerHTML = d.models.map((m) => `<option>${esc(m.name)}</option>`).join("") || "<option value=''>no models</option>";
    $("#status").textContent = d.error || `${d.backend} · ${d.models.length} models`;
  } catch { $("#status").textContent = "core offline"; }
})();

// ---------- model setup progress (download runs in the core's background thread) ----------
(async function setupPoll() {
  try {
    const s = await (await fetch("/api/setup")).json();
    const st = $("#status");
    if (s.state === "pulling" && s.total) {
      const pct = Math.floor((100 * s.completed) / s.total);
      st.textContent = `Downloading qwen-abliterated: ${pct}% (${(s.completed / 2 ** 30).toFixed(2)} of ${(s.total / 2 ** 30).toFixed(2)} GB)`;
    } else if (["checking", "pulling", "copying"].includes(s.state)) {
      st.textContent = `Setting up qwen-abliterated: ${s.status}`;
    } else if (s.state === "error") { st.textContent = s.error; return; }
    else if (s.state === "ready") { return; }
  } catch { return; }
  setTimeout(setupPoll, 1500);
})();
