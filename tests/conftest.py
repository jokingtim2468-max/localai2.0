import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("NIGHTCREW_DATA", str(tmp_path / "data"))
    from nightcrew import skills
    skills.SKILLS.clear()
    yield tmp_path / "data"


class FakeBackend:
    """Plays back scripted rounds: each round is (content, tool_calls)."""
    kind = "fake"

    def __init__(self, rounds):
        self.rounds, self.seen = list(rounds), []

    def models(self):
        return [{"name": "fake"}]

    def chat(self, model, messages, options=None):
        return "summary"

    def stream_chat(self, model, messages, tools=None, options=None, think=None, keep_alive=None):
        self.seen.append([dict(m) for m in messages])
        content, calls = self.rounds.pop(0) if self.rounds else ("done.", [])
        yield {"content": content, "thinking": "", "tool_calls": calls, "done": True}


def call(name, **args):
    return {"function": {"name": name, "arguments": args}}
