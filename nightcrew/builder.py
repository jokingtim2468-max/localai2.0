"""Builder tab backend: the model drafts a screen as a list of elements, the user edits it
by hand, and can ask the model to change one element (right-click) or the whole layout.

An element: {"id","type","x","y","w","h","text","style":{...},"options":[...]}
types: heading text button input textarea checkbox select image box divider
Coordinates are pixels on a 1200x800 canvas.
"""
from __future__ import annotations

import json
import re
import uuid

from . import backends, sandbox, settings

TYPES = ["heading", "text", "button", "input", "textarea", "checkbox", "select", "image", "box", "divider"]

SPEC = """Reply with JSON only, no prose. Canvas is 1200x800 px, dark theme (#0A0A0A background).
Element fields: id (short string), type (one of: %s), x, y, w, h (integers, px),
text (label / placeholder / content), style (optional: color, bg, size, weight, radius, align),
options (list of strings, select only). Keep elements inside the canvas, aligned to an 8px grid,
with consistent spacing. Accent colour #FF6D00 only for primary buttons.""" % ", ".join(TYPES)


def _json(text: str):
    """First JSON object or array in the model's reply."""
    m = re.search(r"```(?:json)?\s*([\[{].*?)```", text, re.S)
    raw = m.group(1) if m else text[text.find("{") if "{" in text else text.find("["):]
    for end in range(len(raw), 0, -1):
        if raw[end - 1] in "}]":
            try:
                return json.loads(raw[:end])
            except ValueError:
                continue
    raise ValueError("the model did not return JSON")


def clean(el: dict) -> dict:
    """Clamp whatever the model sent into a valid element."""
    t = el.get("type") if el.get("type") in TYPES else "text"
    num = lambda k, d, lo, hi: max(lo, min(hi, int(float(el.get(k, d) or d))))
    out = {"id": str(el.get("id") or uuid.uuid4().hex[:6]), "type": t,
           "x": num("x", 40, 0, 1180), "y": num("y", 40, 0, 780),
           "w": num("w", 200, 8, 1200), "h": num("h", 40, 2, 800),
           "text": str(el.get("text", "")), "style": el.get("style") if isinstance(el.get("style"), dict) else {}}
    if t == "select":
        out["options"] = [str(o) for o in (el.get("options") or ["Option 1", "Option 2"])][:20]
    return out


def _model():
    cfg = settings.load()
    return backends.get(cfg["backend"], cfg.get("backend_url", "")), cfg.get("model") or "qwen-abliterated"


def generate(prompt: str, backend=None) -> list[dict]:
    be, model = (backend, "fake") if backend else _model()
    reply = be.chat(model, [{"role": "system", "content": SPEC + '\nReturn {"elements": [...]}.'},
                            {"role": "user", "content": "Lay out this screen: " + prompt}])
    data = _json(reply)
    items = data.get("elements", []) if isinstance(data, dict) else data
    return [clean(e) for e in items if isinstance(e, dict)][:80]


def edit(element: dict, doc: list, instruction: str, backend=None) -> dict:
    be, model = (backend, "fake") if backend else _model()
    others = [{k: e.get(k) for k in ("id", "type", "x", "y", "w", "h", "text")} for e in doc if e.get("id") != element.get("id")][:40]
    reply = be.chat(model, [{"role": "system", "content": SPEC + "\nReturn ONLY the one updated element as a JSON object, same id."},
                            {"role": "user", "content": f"Other elements (context): {json.dumps(others)}\n\n"
                                                        f"Element to change: {json.dumps(element)}\n\nChange: {instruction}"}])
    out = clean(_json(reply))
    out["id"] = element.get("id", out["id"])
    return out


def _css(el: dict) -> str:
    s = el.get("style", {})
    parts = [f"left:{el['x']}px", f"top:{el['y']}px", f"width:{el['w']}px", f"height:{el['h']}px"]
    for k, css in (("color", "color"), ("bg", "background"), ("weight", "font-weight"), ("align", "text-align")):
        if s.get(k):
            parts.append(f"{css}:{s[k]}")
    if s.get("size"):
        parts.append(f"font-size:{int(s['size'])}px")
    if s.get("radius") is not None:
        parts.append(f"border-radius:{int(s['radius'])}px")
    return ";".join(parts)


def to_html(doc: list, title: str = "Screen") -> str:
    from html import escape as e
    rows = []
    for el in doc:
        t, txt, st = el["type"], e(el.get("text", "")), e(_css(el), quote=True)
        if t == "heading":
            rows.append(f'<h1 style="{st}">{txt}</h1>')
        elif t == "button":
            rows.append(f'<button style="{st}">{txt}</button>')
        elif t == "input":
            rows.append(f'<input style="{st}" placeholder="{txt}">')
        elif t == "textarea":
            rows.append(f'<textarea style="{st}" placeholder="{txt}"></textarea>')
        elif t == "checkbox":
            rows.append(f'<label style="{st}"><input type="checkbox"> {txt}</label>')
        elif t == "select":
            opts = "".join(f"<option>{e(o)}</option>" for o in el.get("options", []))
            rows.append(f'<select style="{st}">{opts}</select>')
        elif t == "image":
            rows.append(f'<img style="{st};object-fit:cover" src="{txt}" alt="">')
        elif t == "divider":
            rows.append(f'<hr style="{st};border:0;border-top:1px solid #262626">')
        elif t == "box":
            rows.append(f'<div style="{st};border:1px solid #262626">{txt}</div>')
        else:
            rows.append(f'<p style="{st}">{txt}</p>')
    css = ("body{margin:0;background:#0A0A0A;color:#E0E0E0;font-family:system-ui,sans-serif}"
           ".c{position:relative;width:1200px;height:800px;margin:0 auto}"
           ".c>*{position:absolute;box-sizing:border-box;margin:0}"
           "button{background:#1A1A1A;color:#E0E0E0;border:1px solid #262626;border-radius:6px}"
           "input,textarea,select{background:#121212;color:#E0E0E0;border:1px solid #262626;border-radius:6px;padding:6px 8px}")
    return (f"<!doctype html><html><head><meta charset='utf-8'><title>{e(title)}</title>"
            f"<style>{css}</style></head><body><div class='c'>\n" + "\n".join(rows) + "\n</div></body></html>\n")


def save(name: str, doc: list) -> str:
    name = re.sub(r"[^\w\- ]", "", name or "screen").strip() or "screen"
    sandbox.write_file(f"builder/{name}.json", json.dumps(doc, indent=1))
    sandbox.write_file(f"builder/{name}.html", to_html(doc, name))
    return f"builder/{name}.html"
