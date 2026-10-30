import pytest
from fastapi.testclient import TestClient

from karakeep_yt_download_api import main
from karakeep_yt_download_api.config import Settings, get_settings
from karakeep_yt_download_api.youtube import is_youtube_video_url


@pytest.fixture
def settings(tmp_path):
    return Settings(
        webhook_token="secret",
        library_path=tmp_path,
        jellyfin_url="http://jf:8096",
        jellyfin_api_key="key",
        jellyfin_library_id="lib",
    )


@pytest.fixture
def client(settings, monkeypatch):
    calls = []

    async def fake_process(url, _settings, _client):
        calls.append(url)

    monkeypatch.setattr(main, "_process", fake_process)
    main.app.dependency_overrides[get_settings] = lambda: settings
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    with TestClient(main.app) as c:
        c.calls = calls
        yield c
    main.app.dependency_overrides.clear()


AUTH = {"Authorization": "Bearer secret"}
BODY = {"operation": "created", "type": "link", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}


@pytest.mark.parametrize(
    "url",
    ["https://youtu.be/dQw4w9WgXcQ", "https://m.youtube.com/watch?v=x", "https://www.youtube.com/shorts/abc"],
)
def test_accepts_video_urls(url):
    assert is_youtube_video_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.com/?u=youtube.com/watch",
        "https://youtube.com.evil.com/watch?v=x",
        "https://www.youtube.com/@channel",
        "ftp://youtube.com/watch?v=x",
        "https://youtu.be/",
    ],
)
def test_rejects_other_urls(url):
    assert not is_youtube_video_url(url)


def test_requires_token(client):
    assert client.post("/webhook", json=BODY).status_code == 401
    assert client.post("/webhook", json=BODY, headers={"Authorization": "Bearer nope"}).status_code == 401


def test_queues_youtube(client):
    r = client.post("/webhook", json=BODY, headers=AUTH)
    assert r.status_code == 202
    assert r.json() == {"status": "queued"}


def test_ignores_non_youtube_and_other_events(client):
    assert client.post("/webhook", json={**BODY, "url": "https://example.com"}, headers=AUTH).json() == {
        "status": "ignored"
    }
    assert client.post("/webhook", json={**BODY, "operation": "crawled"}, headers=AUTH).json() == {"status": "ignored"}
