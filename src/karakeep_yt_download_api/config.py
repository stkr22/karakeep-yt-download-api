"""Application settings, loaded from ``KYT_*`` environment variables."""

from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Secrets may also be provided as files in ``KYT_SECRETS_DIR`` (one file per field name).
    """

    model_config = SettingsConfigDict(env_prefix="KYT_", secrets_dir=None, extra="ignore")

    webhook_token: SecretStr
    """Bearer token Karakeep sends with every webhook call."""

    library_path: Path
    """Directory of the Jellyfin YouTube library (the mounted NFS subfolder)."""

    jellyfin_url: str
    """Base URL of Jellyfin, e.g. ``http://jellyfin.media.svc:8096``."""
    jellyfin_api_key: SecretStr
    jellyfin_library_id: str
    """Item ID of the YouTube library (virtual folder) to refresh after a download."""
    jellyfin_timeout_sec: float = 30.0

    ytdlp_format: str = "bestvideo*+bestaudio/best"
    ytdlp_merge_format: str = "mkv"
    channel_folders: bool = True
    """One folder per channel (``<Channel>/<Title> [id].ext``) if true, else flat (``<Title> [id].ext``)."""
    ytdlp_cookies_file: Path | None = None
    """Optional Netscape cookies.txt for age-gated or members-only videos."""
    ytdlp_archive_file: Path | None = None
    """Download archive; defaults to ``<library_path>/.yt-dlp-archive.txt``."""

    queue_size: int = 100

    @property
    def output_template(self) -> str:
        """yt-dlp output template relative to the library."""
        name = "%(title)s [%(id)s].%(ext)s"
        return f"%(channel,uploader|Unknown)s/{name}" if self.channel_folders else name

    @property
    def archive_file(self) -> Path:
        """Resolved download archive path."""
        return self.ytdlp_archive_file or self.library_path / ".yt-dlp-archive.txt"


@lru_cache
def get_settings() -> Settings:
    """Return the cached settings instance."""
    return Settings()
