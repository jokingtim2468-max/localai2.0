import updater


def test_updater_skips_when_not_frozen(monkeypatch):
    monkeypatch.setattr(updater.sys, "frozen", False, raising=False)
    assert updater.check_and_update() is False


def test_updater_reads_build_from_release(monkeypatch):
    import io
    import json
    body = {"body": "Latest Windows build. build: abc1234def", "assets": [{"name": "EclipseSetup.exe", "browser_download_url": "https://x/EclipseSetup.exe"}]}
    monkeypatch.setattr(updater.urllib.request, "urlopen", lambda *a, **k: io.BytesIO(json.dumps(body).encode()))
    assert updater.latest() == ("abc1234def", "https://x/EclipseSetup.exe")
