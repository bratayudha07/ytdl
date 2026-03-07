"""
utils.py
========
Pure stateless helper functions: filename sanitization,
URL validation, and exponential backoff sleep.
"""

import time
import urllib.parse
import logging

from ytdl.constants import _ILLEGAL_CHARS, _TRAILING_JUNK, RETRY_BACKOFF_BASE

logger = logging.getLogger("ytdl")


def sanitize_filename(name: str, max_len: int = 200) -> str:
    """Strip illegal filesystem characters and truncate to max_len."""
    name = _ILLEGAL_CHARS.sub("_", name)
    name = _TRAILING_JUNK.sub("", name).strip()
    return (name[:max_len].rstrip() if len(name) > max_len else name) or "untitled"


def validate_url(url: str) -> bool:
    """Return True only for well-formed http/https URLs."""
    url = url.strip()
    p = urllib.parse.urlparse(url)
    return p.scheme in ("http", "https") and bool(p.netloc) and len(url) >= 10


def exponential_backoff(attempt: int) -> None:
    """Sleep for min(base^attempt, 60) seconds before a retry."""
    wait = min(RETRY_BACKOFF_BASE ** attempt, 60)
    logger.debug(f"Backoff {attempt + 1}: {wait}s")
    time.sleep(wait)
