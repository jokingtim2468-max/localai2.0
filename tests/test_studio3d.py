import base64

from nightcrew import server, settings


def test_studio3d_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "load", lambda: {**settings.DEFAULTS, "workdir": str(tmp_path)})
    (tmp_path / "m").mkdir()
    (tmp_path / "m" / "a.glb").write_bytes(b"glTF-old")
    c = server.app.test_client()
    H = {"X-NC": "1"}
    assert [m["path"] for m in c.get("/api/model3d/list").get_json()["models"]] == ["m/a.glb"]
    assert c.get("/api/model3d/file?path=m/a.glb").data == b"glTF-old"
    assert c.get("/api/model3d/file?path=../x.glb").status_code == 400          # outside the workspace
    r = c.post("/api/model3d/save", json={"path": "m/a.glb", "b64": base64.b64encode(b"glTF-new").decode()}, headers=H)
    assert r.get_json()["ok"] and (tmp_path / "m" / "a.glb").read_bytes() == b"glTF-new"
    assert (tmp_path / "m" / "a.glb.bak").read_bytes() == b"glTF-old"
    assert c.post("/api/model3d/save", json={"path": "m/a.txt", "b64": ""}, headers=H).status_code == 400
    assert c.post("/api/model3d/comment", json={"path": "m/a.glb", "part": "Slide", "text": "make it longer"}).status_code == 403
    d = c.post("/api/model3d/comment", json={"path": "m/a.glb", "part": "Slide", "text": "make it longer"}, headers=H).get_json()
    assert d["comments"][-1]["part"] == "Slide"
    p = c.post("/api/model3d/prompt", json={"path": "m/a.glb", "part": "Slide", "text": "make it longer"}, headers=H).get_json()["prompt"]
    assert "Slide" in p and "make it longer" in p and str(tmp_path) in p
