import json

from conftest import FakeBackend, call
from nightcrew import agent, escalation, model_setup


class Resp:
    def __init__(self, data=None, lines=None, code=200):
        self.data, self.lines, self.status_code, self.text = data, lines or [], code, ""

    def json(self):
        return self.data

    def raise_for_status(self):
        pass

    def iter_lines(self):
        return iter(self.lines)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def fake_ollama(monkeypatch, have):
    log = []
    monkeypatch.setattr(model_setup.httpx, "get", lambda url, **k: Resp(
        {"version": "x"} if url.endswith("/version") else {"models": [{"name": n} for n in have]}))

    def stream(method, url, json=None, **k):
        log.append(("pull", json["model"]))
        return Resp(lines=[__import__("json").dumps({"status": "pulling", "total": 100, "completed": 50}),
                           __import__("json").dumps({"status": "success"})])

    def post(url, json=None, **k):
        log.append(("copy", json["source"], json["destination"]))
        return Resp({})
    monkeypatch.setattr(model_setup.httpx, "stream", stream)
    monkeypatch.setattr(model_setup.httpx, "post", post)
    return log


def test_setup_pulls_then_copies_when_missing(monkeypatch):
    log = fake_ollama(monkeypatch, [])
    seen = []
    r = model_setup.ensure(on_progress=seen.append)
    assert r["state"] == "ready"
    assert log == [("pull", model_setup.SOURCE), ("copy", model_setup.SOURCE, "qwen-abliterated")]
    assert seen[0]["completed"] == 50


def test_setup_only_copies_when_source_present(monkeypatch):
    log = fake_ollama(monkeypatch, [model_setup.SOURCE])
    model_setup.ensure()
    assert log == [("copy", model_setup.SOURCE, "qwen-abliterated")]


def test_setup_does_nothing_when_alias_present(monkeypatch):
    log = fake_ollama(monkeypatch, ["qwen-abliterated:latest"])
    assert model_setup.ensure()["state"] == "ready" and log == []


def test_every_tier_uses_the_resident_model_and_stays_loaded():
    be = FakeBackend([("fix it", [])] * 10)
    seen = []
    orig = be.stream_chat
    be.stream_chat = lambda m, msgs, **k: (seen.append((m, k.get("keep_alive"))), orig(m, msgs, **k))[1]
    out = escalation.escalate("boom", "swarm", backend=be)
    assert out.startswith("[swarm]") and out.count("[swarm ") == 3 and "mr_debug" in out
    assert {m for m, _ in seen} == {"qwen-abliterated"}


def test_two_failed_runs_push_to_buddy():
    ev = []
    be = FakeBackend([("", [call("run_command", command="exit 1")]),
                      ("", [call("run_command", command="exit 2")]), ("ok", [])])
    agent.run_turn([{"role": "user", "content": "build"}], lambda e, d: ev.append((e, d)),
                   backend=be, model="fake", ask=False)
    assert any(e == "notice" and "buddy" in d for e, d in ev)
    assert "tier='buddy'" in json.dumps(be.seen[-1])


def test_recommend_two_lists_sorted_by_fit():
    from nightcrew import catalog
    r = catalog.recommend({"vram_gb": 8}, installed={"qwen-abliterated:latest"})
    assert all("abliterat" in m["name"] for m in r["abliterated"])
    assert not any("abliterat" in m["name"] for m in r["regular"])
    fits = [m["fit"] for m in r["abliterated"]]
    assert fits == sorted(fits, key=["fits", "tight", "too big"].index)
    assert next(m for m in r["abliterated"] if m["name"] == "qwen-abliterated")["installed"]
    assert next(m for m in r["regular"] if m["name"] == "llama3.3:70b")["fit"] == "too big"
