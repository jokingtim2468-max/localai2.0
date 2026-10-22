import pytest

from conftest import FakeBackend, call
from nightcrew import agent, context, memory, sandbox, settings, skills


def run(rounds, **kw):
    ev = []
    be = FakeBackend(rounds)
    agent.run_turn([{"role": "user", "content": kw.pop("ask_text", "build it")}],
                   lambda e, d: ev.append((e, d)), backend=be, model="fake", **kw)
    return ev, be


def test_jail_blocks_escape():
    with pytest.raises(sandbox.ToolError):
        sandbox.jail("../../etc/passwd")
    assert "outside" in sandbox.run_tool("write_file", {"path": "../x.txt", "content": "no"})


def test_write_read_edit_delete():
    assert sandbox.run_tool("write_file", {"path": "a/b.txt", "content": "hello world"}).startswith("OK")
    assert sandbox.read_file("a/b.txt") == "hello world"
    assert sandbox.run_tool("edit_file", {"path": "a/b.txt", "old": "world", "new": "there"}).startswith("OK")
    assert sandbox.read_file("a/b.txt") == "hello there"
    assert sandbox.run_tool("delete_file", {"path": "a"}).startswith("error")      # not empty
    assert sandbox.run_tool("delete_file", {"path": "a", "recursive": True}).startswith("OK")
    assert "won't delete" in sandbox.run_tool("delete_file", {"path": "."})


def test_missing_file_suggests_real_ones():
    sandbox.write_file("Main.java", "x")
    r = sandbox.run_tool("read_file", {"path": "main.jav"})
    assert r.startswith("error") and "Main.java" in r


def test_run_command_in_workspace():
    r = sandbox.run_command("echo hi")
    assert r.startswith("OK") and "hi" in r
    assert sandbox.run_command("exit 3").startswith("FAILED")


def test_memory_same_key_overwrites():
    memory.remember("theme: dark")
    memory.remember("theme: light")
    assert memory.lines() == ["theme: light"]


def test_compaction_summarises_and_keeps_recent():
    msgs = [{"role": "system", "content": "sys"}] + [
        {"role": "user" if i % 2 == 0 else "assistant", "content": "x" * 500} for i in range(20)]
    info = context.compact(msgs, 4000, lambda t: "they want a game")
    assert info["compacted"] > 0
    assert msgs[1]["content"].startswith("[earlier in this chat]")
    assert msgs[0]["content"] == "sys"


def test_compaction_never_orphans_tool_result():
    msgs = [{"role": "system", "content": "s"}] + [{"role": "user", "content": "y" * 800}] * 6 + [
        {"role": "assistant", "content": "", "tool_calls": [1]}, {"role": "tool", "content": "z" * 800}] + [
        {"role": "user", "content": "q"}] * 5
    context.compact(msgs, 2000, lambda t: "s", keep_recent=6)
    assert msgs[1]["role"] != "tool"


def test_skill_routing_typos(data_dir):
    d = data_dir / "skills"
    for name, trig in (("cpp", "cmake, c++"), ("blender", "blender, cube, mesh")):
        (d / name).mkdir(parents=True)
        (d / name / "SKILL.md").write_text(f"---\nname: {name}\ndomain: {name}\ntriggers: [{trig}]\n---\nbody")
    skills.scan()
    assert skills.domain_of("make a cube in blender") == "blender"
    assert skills.domain_of("make a cube in blendr") == "blender"      # typo
    assert skills.domain_of("make a thing") == ""                       # make != cmake


def test_agent_runs_tool_then_answers():
    ev, be = run([("", [call("write_file", path="hi.py", content="print(1)")]), ("Wrote hi.py.", [])])
    names = [e for e, _ in ev]
    assert names.count("tool_call") == 1 and names[-1] == "done"
    assert sandbox.read_file("hi.py") == "print(1)"


def test_repeat_guard_allows_rerun_after_write():
    ev, _ = run([("", [call("run_command", command="echo a")]),
                 ("", [call("write_file", path="f.txt", content="1")]),
                 ("", [call("run_command", command="echo a")]),      # after a write: allowed
                 ("ok", [])], ask=False)
    results = [d["result"] for e, d in ev if e == "tool_result"]
    assert all("already called" not in r for r in results)


def test_repeat_guard_blocks_true_repeat():
    ev, _ = run([("", [call("remember", note="a: b")]), ("", [call("remember", note="a: b")]), ("ok", [])])
    assert any("already called" in d["result"] for e, d in ev if e == "tool_result")


def test_approval_denied_runs_nothing():
    ev = []
    agent.run_turn([{"role": "user", "content": "go"}], lambda e, d: ev.append((e, d)),
                   approve=lambda n, a: False, backend=FakeBackend(
                       [("", [call("run_command", command="echo pwned > owned.txt")]), ("ok", [])]), model="fake")
    assert not (sandbox.workspace() / "owned.txt").exists()


def test_trusted_workspace_skips_approval_for_files_only():
    assert not agent.needs_approval("write_file", True)
    assert agent.needs_approval("run_command", True)
    settings.save({"trust_workspace": False})
    assert agent.needs_approval("write_file", True)


def test_turn_never_ends_empty():
    ev, _ = run([("", [])])
    assert any(e == "token" and d.strip() for e, d in ev)


def test_memory_in_system_prompt():
    memory.remember("lang: rust")
    assert "lang: rust" in agent.system_prompt("x")


def test_server_guards_and_routes():
    from nightcrew.server import app
    c = app.test_client()
    assert c.get("/api/health").json["ok"]
    assert c.post("/api/settings", json={"think": True}).status_code == 403
    assert c.post("/api/settings", json={"think": True, "evil": 1}, headers={"X-NC": "1"}).json["think"] is True
    assert "evil" not in settings.load()
    assert c.post("/api/chat", json={}).status_code == 403
    assert c.get("/api/models").status_code == 200        # offline backend -> error field, not a crash


def test_cors_only_for_eclipse_origins():
    from nightcrew.server import app
    c = app.test_client()
    ok = c.options("/api/chat", headers={"Origin": "tauri://localhost"})
    assert ok.headers.get("Access-Control-Allow-Origin") == "tauri://localhost"
    bad = c.options("/api/chat", headers={"Origin": "https://evil.example"})
    assert "Access-Control-Allow-Origin" not in bad.headers


def test_hardware_recommend_tiers():
    from nightcrew import hardware
    assert "32b" in hardware.recommend({"apple_silicon": True, "ram_gb": 36})["models"][0]
    assert "7b" in hardware.recommend({"vram_gb": 8})["models"][0]
    assert hardware.recommend({"os": "Darwin", "ram_gb": 16})["warning"].startswith("Intel")
