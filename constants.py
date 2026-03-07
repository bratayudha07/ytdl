"""
constants.py
============
Logging setup, dependency checks, all application-wide constants,
file paths, timeout values, format tables, and default configuration.
"""

import sys
import os
import re
import shutil
import logging
from pathlib import Path

# ───────────────────────────────────────────────────────────────────
# LOGGING SETUP
# ───────────────────────────────────────────────────────────────────

BASE_DIR = Path.home() / ".ytdl_ultimate"
BASE_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = BASE_DIR / "ytdl.log"

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ]
)
logging.getLogger().handlers[1].setLevel(logging.WARNING)
logger = logging.getLogger("ytdl")

# ───────────────────────────────────────────────────────────────────
# DEPENDENCY CHECK
# ───────────────────────────────────────────────────────────────────

try:
    import yt_dlp  # noqa: F401
except ImportError:
    print("\n\033[38;5;196m  x  Modul 'yt-dlp' tidak ditemukan.\033[0m")
    print("     Install: pip install yt-dlp\n")
    sys.exit(1)

try:
    import mutagen  # noqa: F401
    from mutagen.id3 import ID3, USLT, SYLT, Encoding, ID3NoHeaderError  # noqa: F401
    from mutagen.flac import FLAC  # noqa: F401
    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False
    logger.warning("Mutagen tidak ditemukan. Embed lirik tidak tersedia.")

FFMPEG_AVAILABLE = bool(shutil.which("ffmpeg"))
if not FFMPEG_AVAILABLE:
    logger.warning("ffmpeg tidak ditemukan. Konversi audio mungkin gagal.")

# =======================================================================
# APP INFO
# =======================================================================

APP_NAME = "YouTube Ultimate Downloader"
VERSION  = "4.1.0"
TAGLINE  = "Elegant. Stable. Powerful."

# =======================================================================
# FILE PATHS
# =======================================================================

CONFIG_FILE  = BASE_DIR / "config.json"
HISTORY_FILE = BASE_DIR / "history.json"
COOKIE_FILE  = BASE_DIR / "cookies.txt"
LYRICS_CACHE = BASE_DIR / "lyrics_cache.json"

# =======================================================================
# TIMEOUTS & RETRY
# =======================================================================

SOCKET_TIMEOUT       = 30
META_TIMEOUT         = 90
DL_TIMEOUT           = 3600
LYRICS_HTTP_TIMEOUT  = 10
MAX_RETRIES          = 5
RETRY_BACKOFF_BASE   = 2
MAX_PLAYLIST_WORKERS = 3

# =======================================================================
# FORMAT TABLES
# =======================================================================

AUDIO_FORMATS: dict = {
    "mp3"  : ("MP3  - Lossy",           False),
    "flac" : ("FLAC - Lossless",         True),
    "wav"  : ("WAV  - Lossless PCM",     True),
    "opus" : ("Opus - Lossy efisien",    False),
    "m4a"  : ("M4A  - AAC Lossy",        False),
}
VALID_VIDEO_RESOLUTIONS: dict = {
    "max"  : "Terbaik   (Max)",
    "1080" : "1080p   Full HD",
    "720"  : " 720p   HD",
    "480"  : " 480p   SD",
    "360"  : " 360p   Low",
}
VALID_AUDIO_QUALITIES = {"64", "96", "128", "160", "192", "256", "320", "0"}

# =======================================================================
# FILENAME HELPERS
# =======================================================================

_ILLEGAL_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_TRAILING_JUNK = re.compile(r'[\s.]+$')


def _default_path(sub: str) -> str:
    sdcard = Path("/sdcard/Download")
    return str(sdcard / sub) if sdcard.exists() else str(Path.home() / "Downloads" / sub)


# =======================================================================
# DEFAULT CONFIGURATION
# =======================================================================

DEFAULT_CONFIG: dict = {
    "path_video"      : _default_path("YTDL_Video"),
    "path_audio"      : _default_path("YTDL_Music"),
    "use_aria2c"      : True,
    "max_connections" : 10,
    "embed_thumbnail" : True,
    "embed_metadata"  : True,
    "embed_subs"      : True,
    "embed_chat"      : True,
    "embed_lyrics"    : True,
    "save_lrc_file"   : False,
    "video_resolution": "1080",
    "audio_format"    : "mp3",
    "audio_quality"   : "192",
}
