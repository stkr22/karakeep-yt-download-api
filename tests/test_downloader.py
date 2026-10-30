import httpx
import pytest

from karakeep_yt_download_api import downloader, jellyfin
from karakeep_yt_download_api.config import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        webhook_token="t",
        library_path=tmp_path,
        jellyfin_url="http://jf:8096/",
        jellyfin_api_key="key",
        jellyfin_library_id="lib123",
        ytdlp_cookies_file=tmp_path / "c.txt",
    )


def test_options(settings):
    opts = downloader.build_options(settings)
    assert opts["outtmpl"].endswith("/%(channel,uploader|Unknown)s/%(title)s [%(id)s].%(ext)s")
    assert opts["writeinfojson"]
    assert opts["writethumbnail"]
    assert opts["noplaylist"]
    assert opts["cookiefile"].endswith("c.txt")


async def test_refresh_calls_library_only(settings):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = request.url.path
        seen["auth"] = request.headers["Authorization"]
        return httpx.Response(204)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await jellyfin.refresh_library(client, settings)
    assert seen == {"url": "/Items/lib123/Refresh", "auth": 'MediaBrowser Token="key"'}


def test_flat_layout(settings):
    settings.channel_folders = False
    opts = downloader.build_options(settings)
    assert opts["outtmpl"] == f"{settings.library_path}/%(title)s [%(id)s].%(ext)s"
