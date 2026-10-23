"""HTTP API for the core. Used by the Night Crew web UI (static/) and by Eclipse's
sidecar. Binds 127.0.0.1 only. State-changing routes need header X-NC: 1 (a page on
another origin cannot set it without a CORS preflight we never grant).

python -m nightcrew.server [--port 5173]
"""
from __future__ import annotations

import json
import os
import queue
import threading
import uuid

from flask import Flask, Response, jsonify, request, send_from_directory

from . import agent, backends, memory, paths, sandbox, settings, skills

STATIC = paths.HERE.parent / "static"
app = Flask(__name__, static_folder=None)
PENDING: dict[str, dict] = {}


# Eclipse's webview (Tauri) and its Vite dev server are the only other origins allowed in.
ALLOWED_ORIGINS = {"tauri://localhost", "http://tauri.localhost", "https://tauri.localhost",
                   "http://localhost:1420", "http://127.0.0.1:1420"}


@app.before_request
def preflight():
    if request.method == "OPTIONS":
        return Response(status=204)


@app.after_request
def cors(resp):
    origin = request.headers.get("Origin", "")
    if origin in ALLOWED_ORIGINS:
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-NC"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
        resp.headers["Vary"] = "Origin"
    return resp


def guard():
    if request.headers.get("X-NC") != "1":
        return jsonify({"error": "missing X-NC header"}), 403
    return None


ECLIPSE = paths.HERE.parent / "eclipse" / "dist"


@app.get("/")
def index():
    # The desktop window shows Eclipse when it is built; Night Crew's page otherwise.
    if (ECLIPSE / "index.html").is_file():
        return send_from_directory(ECLIPSE, "index.html")
    return send_from_directory(STATIC, "index.html")


@app.get("/assets/<path:p>")
def eclipse_assets(p):
    return send_from_directory(ECLIPSE / "assets", p)


@app.get("/nightcrew")
def nightcrew_page():
    return send_from_directory(STATIC, "index.html")


@app.get("/static/<path:p>")
def static_files(p):
    return send_from_directory(STATIC, p)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "version": __import__("nightcrew").__version__})


@app.route("/api/settings", methods=["GET", "POST"])
def api_settings():
    if request.method == "POST":
        if (g := guard()):
            return g
        allowed = set(settings.DEFAULTS)
        return jsonify(settings.save({k: v for k, v in (request.get_json(force=True) or {}).items() if k in allowed}))
    return jsonify(settings.load())


@app.get("/api/models")
def api_models():
    cfg = settings.load()
    try:
        return jsonify({"backend": cfg["backend"], "models": backends.get(cfg["backend"], cfg.get("backend_url", "")).models()})
    except Exception as e:
        return jsonify({"backend": cfg["backend"], "models": [], "error": f"{cfg['backend']} offline: {e}"})


@app.get("/api/hardware")
def api_hardware():
    from . import hardware
    info = hardware.detect()
    return jsonify({"info": info, "recommend": hardware.recommend(info), "power": hardware.power()})


@app.get("/api/power")
def api_power():
    from . import hardware
    return jsonify(hardware.power())


def _backend():
    cfg = settings.load()
    return backends.get(cfg["backend"], cfg.get("backend_url", ""))


@app.post("/api/models/bench")
def api_bench():
    if (g := guard()):
        return g
    try:
        return jsonify(_backend().bench((request.get_json(force=True) or {}).get("model", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.post("/api/models/pull")
def api_pull():
    if (g := guard()):
        return g
    name = (request.get_json(force=True) or {}).get("model", "")
    from . import model_setup
    if name == model_setup.ALIAS:                 # not on the registry: pull the HF file + copy
        threading.Thread(target=model_setup.ensure, daemon=True).start()
        return jsonify({"ok": True, "setup": True})
    be = _backend()
    if not hasattr(be, "pull"):
        return jsonify({"error": f"{be.kind} cannot pull; download the GGUF/MLX model yourself"}), 400

    def stream():
        try:
            for d in be.pull(name):
                yield sse("progress", d)
        except Exception as e:
            yield sse("error", str(e))
        yield sse("done", {})
    return Response(stream(), mimetype="text/event-stream")


@app.post("/api/models/delete")
def api_delete():
    if (g := guard()):
        return g
    be = _backend()
    ok = hasattr(be, "delete") and be.delete((request.get_json(force=True) or {}).get("model", ""))
    return jsonify({"ok": bool(ok)})


@app.post("/api/models/stop")
def api_stop():
    if (g := guard()):
        return g
    try:
        be = _backend()
        return jsonify({"stopped": be.stop_all() if hasattr(be, "stop_all") else 0})
    except Exception as e:
        return jsonify({"error": str(e)}), 502


@app.get("/api/recommend")
def api_recommend():
    from . import catalog
    try:
        have = {m["name"] for m in _backend().models()}
    except Exception:
        have = set()
    return jsonify(catalog.recommend(installed=have))


@app.post("/api/builder/<action>")
def api_builder(action):
    if (g := guard()):
        return g
    from . import builder
    b = request.get_json(force=True) or {}
    try:
        if action == "generate":
            return jsonify({"elements": builder.generate(b.get("prompt", ""))})
        if action == "edit":
            return jsonify({"element": builder.edit(b.get("element", {}), b.get("doc", []), b.get("instruction", ""))})
        if action == "save":
            return jsonify({"path": builder.save(b.get("name", "screen"), [builder.clean(x) for x in b.get("doc", [])])})
    except Exception as e:
        return jsonify({"error": str(e)}), 502
    return jsonify({"error": "unknown action"}), 404


@app.route("/api/web/key", methods=["GET", "POST"])
def api_web_key():
    from . import web
    if request.method == "POST":
        if (g := guard()):
            return g
        ok = web.set_key((request.get_json(force=True) or {}).get("key", ""))
        return jsonify({"ok": ok, "error": "" if ok else "no system keychain available (pip install keyring)"})
    return jsonify({"set": bool(web._key())})        # never send the key itself back


@app.get("/api/train")
def api_train():
    from .training import auto, dataset, runner
    ok, why = runner.ready()
    plan = auto.pick(1000)
    return jsonify({**runner.STATE, "tools_ready": ok, "tools_why": why, "plan": plan,
                    "defaults": dataset.DEFAULTS, "your_turns": len(dataset.load_traces())})


@app.post("/api/train/<action>")
def api_train_action(action):
    if (g := guard()):
        return g
    from .training import runner
    if action == "start":
        return jsonify({"started": runner.start((request.get_json(force=True) or {}).get("opts", {}))})
    if action == "stop":
        return jsonify({"stopped": runner.stop()})
    return jsonify({"error": "unknown action"}), 404


@app.get("/api/setup")
def api_setup():
    from . import model_setup
    return jsonify(model_setup.SETUP)


@app.get("/api/memory")
def api_memory():
    return jsonify({"text": memory.text()})


@app.get("/api/skills")
def api_skills():
    skills.scan()
    return jsonify([{k: s[k] for k in ("name", "description", "domain")} for s in skills.SKILLS.values()])


@app.get("/api/tree")
def api_tree():
    try:
        return jsonify({"root": str(sandbox.workspace()), "items": sandbox.list_dir(request.args.get("path", ".")).splitlines()})
    except sandbox.ToolError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/file")
def api_file():
    try:
        return jsonify({"text": sandbox.read_file(request.args.get("path", ""))})
    except sandbox.ToolError as e:
        return jsonify({"error": str(e)}), 400


@app.get("/api/model3d/list")
def api_m3d_list():
    from . import studio3d
    return jsonify({"root": str(sandbox.workspace()), "models": studio3d.list_models()})


@app.get("/api/model3d/file")
def api_m3d_file():
    from . import studio3d
    try:
        p = studio3d.model_path(request.args.get("path", ""))
        return send_from_directory(p.parent, p.name, max_age=0)
    except sandbox.ToolError as e:
        return jsonify({"error": str(e)}), 400


@app.post("/api/model3d/<action>")
def api_m3d_action(action):
    if (g := guard()):
        return g
    from . import studio3d
    b = request.get_json(force=True) or {}
    try:
        if action == "save":
            return jsonify(studio3d.save(b.get("path", ""), b.get("b64", "")))
        if action == "comment":
            return jsonify({"comments": studio3d.add_comment(b.get("path", ""), b.get("part", ""), b.get("text", ""), b.get("point"))})
        if action == "comments":
            return jsonify({"comments": studio3d.comments(b.get("path", ""))})
        if action == "create":
            return jsonify(studio3d.create_prompt(b.get("name", ""), b.get("desc", "")))
        if action == "prompt":
            return jsonify({"prompt": studio3d.agent_prompt(b.get("path", ""), b.get("part", ""), b.get("text", ""), b.get("info"))})
    except (sandbox.ToolError, ValueError) as e:
        return jsonify({"error": str(e)}), 400
    return jsonify({"error": "unknown action"}), 404


@app.route("/api/chats", methods=["GET", "POST"])
def api_chats():
    f = paths.data("chats.json")
    if request.method == "POST":
        if (g := guard()):
            return g
        tmp = str(f) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(request.get_json(force=True), fh)
        os.replace(tmp, f)
        return jsonify({"ok": True})
    try:
        return Response(f.read_text(encoding="utf-8"), mimetype="application/json")
    except OSError:
        return jsonify({"chats": []})


@app.get("/api/system")
def api_system():
    out = {"cpu": None, "ram": None}
    try:
        import psutil
        out = {"cpu": psutil.cpu_percent(interval=0.1), "ram": psutil.virtual_memory().percent}
    except Exception:
        pass
    return jsonify(out)


@app.post("/api/approve")
def api_approve():
    if (g := guard()):
        return g
    body = request.get_json(force=True) or {}
    p = PENDING.get(body.get("id"))
    if not p:
        return jsonify({"ok": False}), 404
    p["allow"] = bool(body.get("allow"))
    p["event"].set()
    return jsonify({"ok": True})


def sse(event: str, data) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@app.post("/api/chat")
def api_chat():
    if (g := guard()):
        return g
    body = request.get_json(force=True) or {}
    q: queue.Queue = queue.Queue()

    def emit(ev, data):
        q.put((ev, data))

    def approve(name, args):
        cid = uuid.uuid4().hex
        PENDING[cid] = {"event": threading.Event(), "allow": False}
        emit("approval", {"id": cid, "tool": name, "args": args})
        PENDING[cid]["event"].wait(timeout=300)
        return PENDING.pop(cid, {}).get("allow", False)

    def work():
        agent.run_turn(body.get("messages", []), emit, approve, model=body.get("model", ""),
                       ask=bool(body.get("ask", True)), use_tools=bool(body.get("tools", True)))
        q.put(None)

    threading.Thread(target=work, daemon=True).start()

    def stream():
        while (item := q.get()) is not None:
            yield sse(*item)

    return Response(stream(), mimetype="text/event-stream", headers={"Cache-Control": "no-cache"})


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("NIGHTCREW_PORT", 5173)))
    a = ap.parse_args(argv)
    skills.seed()
    skills.scan()
    if not os.environ.get("NIGHTCREW_NO_SETUP"):
        from . import model_setup
        model_setup.start_background()      # never blocks: the UI shows progress
    print(f"Night Crew core on http://127.0.0.1:{a.port}", flush=True)
    app.run(host="127.0.0.1", port=a.port, threaded=True)


if __name__ == "__main__":
    main()
