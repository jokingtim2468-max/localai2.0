import json

from conftest import FakeBackend, call
from nightcrew import agent
from nightcrew.training import auto, dataset, evaluate


def turn(*results, answer="done"):
    m = [{"role": "user", "content": "build it"}]
    for name, res in results:
        m += [dataset._call(name), dataset._tool(name, res)]
    return m + [{"role": "assistant", "content": answer}]


def test_classify():
    assert dataset.classify(turn(("run_command", "OK"))) == "good"
    assert dataset.classify(turn(("run_command", "FAILED x"), ("edit_file", "OK"), ("run_command", "OK"))) == "fix"
    assert dataset.classify(turn(("run_command", "FAILED x"))) == ""                      # ended broken
    assert dataset.classify(turn(("run_command", "error: user denied this action"))) == ""
    assert dataset.classify(turn(("run_command", "OK"), answer="")) == ""


def test_secrets_and_emails_are_dropped():
    assert not dataset.clean({"messages": [{"content": "my key is sk-abcdefghijklmnopqrstuvwxyz123"}]})
    assert not dataset.clean({"messages": [{"content": "mail me at someone@example.com"}]})
    assert not dataset.clean({"messages": [{"content": "password = hunter2hunter"}]})
    assert dataset.clean({"messages": [{"content": "std::unique_ptr<int> p;"}]})


def test_recorded_turns_become_training_data():
    ev = []
    agent.run_turn([{"role": "user", "content": "make hi.txt"}], lambda e, d: ev.append(e),
                   backend=FakeBackend([("", [call("write_file", path="hi.txt", content="hi")]), ("Wrote hi.txt.", [])]),
                   model="fake")
    good, fixes = dataset.from_traces()
    assert len(good) == 1 and good[0]["messages"][0]["content"] == "make hi.txt"


def test_build_writes_split_and_counts():
    m = dataset.build({"web": False, "media": False, "cpp": True}, log=lambda s: None)
    assert m["total"] > 300 and m["eval"] == m["total"] // 10
    rows = (dataset.out_dir() / "train.jsonl").read_text().splitlines()
    assert len(rows) == m["total"] - m["eval"]
    assert {"drills", "honesty", "spelling", "reading", "typos"} <= set(m["counts"])
    assert m["cpp"][0]["licence"] == "MIT"


def test_auto_settings_for_a_4060_and_oom_shrink():
    c = auto.pick(800, {"vram_gb": 8.0})
    assert c["ok"] and c["method"] == "unsloth" and c["max_seq_len"] == 2048 and c["load_in_4bit"]
    c2 = auto.shrink(c)
    assert c2["max_seq_len"] == 1024
    assert auto.shrink(c2) is None                    # batch already 1, 1024 tokens: give up
    assert not auto.pick(800, {"ram_gb": 32})["ok"]   # no GPU, not a Mac


def test_evaluate_scores_next_step():
    rows = [{"messages": turn(("run_command", "OK"))}, {"messages": [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]}]
    tests = evaluate.cases(rows)
    assert [w for _, w in tests] == ["run_command", "<answer>"]
    be = FakeBackend([("", [call("run_command", command="x")]), ("hello", [])])
    assert evaluate.score("fake", tests, backend=be, log=lambda s: None) == 100.0
