"""yt-dlp invocation producing Jellyfin-friendly files."""

import logging
from typing import Any

from yt_dlp import YoutubeDL

from karakeep_yt_download_api.config import Settings

logger = logging.getLogger(__name__)


def build_options(settings: Settings) -> dict[str, Any]:
    """Build yt-dlp options: ``[<Channel>/]<Title> [<id>].<ext>`` plus info JSON and JPEG thumbnail sidecars."""
    opts: dict[str, Any] = {
        "outtmpl": str(settings.library_path / settings.output_template),
        "format": settings.ytdlp_format,
        "merge_output_format": settings.ytdlp_merge_format,
        "noplaylist": True,
        "writeinfojson": True,
        "writethumbnail": True,
        "download_archive": str(settings.archive_file),
        "postprocessors": [{"key": "FFmpegThumbnailsConvertor", "format": "jpg", "when": "before_dl"}],
        "quiet": True,
        "no_warnings": True,
        "logger": logger,
    }
    if settings.ytdlp_cookies_file:
        opts["cookiefile"] = str(settings.ytdlp_cookies_file)
    return opts


def download(url: str, settings: Settings) -> bool:
    """Download ``url`` into the library (blocking).

    Returns True if a new video was downloaded, False if the archive already had it.
    Raises ``yt_dlp.utils.DownloadError`` on failure.
    """
    settings.library_path.mkdir(parents=True, exist_ok=True)
    archive = settings.archive_file
    before = archive.stat().st_size if archive.exists() else 0
    with YoutubeDL(build_options(settings)) as ydl:
        ydl.download([url])
    return archive.exists() and archive.stat().st_size > before
