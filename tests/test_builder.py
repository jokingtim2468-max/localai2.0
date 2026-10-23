import json

from nightcrew import builder, sandbox


class Fake:
    kind = "fake"

    def __init__(self, reply):
        self.reply = reply

    def chat(self, model, messages, options=None):
        return self.reply


def test_generate_parses_and_clamps():
    reply = 'Sure!\n```json\n{"elements":[{"id":"t","type":"heading","x":9999,"y":-5,"w":300,"h":40,"text":"Hi"},{"type":"bogus"}]}\n```'
    els = builder.generate("login", backend=Fake(reply))
    assert els[0]["x"] == 1180 and els[0]["y"] == 0 and els[0]["type"] == "heading"
    assert els[1]["type"] == "text"           # unknown type -> text


def test_edit_keeps_id():
    el = {"id": "b1", "type": "button", "x": 10, "y": 10, "w": 100, "h": 30, "text": "Go"}
    out = builder.edit(el, [el], "make it say Start", backend=Fake('{"id":"zzz","type":"button","text":"Start"}'))
    assert out["id"] == "b1" and out["text"] == "Start"


def test_export_escapes_model_text():
    doc = [builder.clean({"type": "text", "text": "<script>x</script>", "style": {"color": 'red" onclick="x'}})]
    html = builder.to_html(doc)
    assert "<script>x" not in html and 'onclick="x' not in html


def test_save_writes_json_and_html():
    p = builder.save("Login Screen!", [builder.clean({"type": "button", "text": "Go"})])
    assert p == "builder/Login Screen.html"
    assert json.loads(sandbox.read_file("builder/Login Screen.json"))[0]["text"] == "Go"
