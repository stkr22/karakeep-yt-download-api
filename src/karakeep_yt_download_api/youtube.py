"""YouTube URL recognition."""

from urllib.parse import urlsplit

_YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
_SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
_VIDEO_PATH_PREFIXES = ("/watch", "/shorts/", "/live/", "/embed/")


def is_youtube_video_url(url: str) -> bool:
    """Return True for http(s) links to a single YouTube video (not channels or playlists)."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
    except ValueError:
        return False
    if parts.scheme not in {"http", "https"}:
        return False
    if host in _SHORT_HOSTS:
        return len(parts.path.strip("/")) > 0
    return host in _YOUTUBE_HOSTS and parts.path.startswith(_VIDEO_PATH_PREFIXES)
