"""
lyrics.py
=========
LyricsManager: fetch synced/plain lyrics from lrclib.net,
cache results locally, embed into MP3 (SYLT/USLT) or FLAC,
and optionally save a .lrc sidecar file.
"""

import re
import json
import hashlib
import logging
import threading
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path

from ytdl.constants import (
    VERSION, LYRICS_CACHE, LYRICS_HTTP_TIMEOUT,
    MUTAGEN_AVAILABLE,
)
from ytdl.utils import sanitize_filename

logger = logging.getLogger("ytdl")

# Lazy imports — only resolved if MUTAGEN_AVAILABLE is True
if MUTAGEN_AVAILABLE:
    from mutagen.id3 import ID3, USLT, SYLT, Encoding, ID3NoHeaderError
    from mutagen.flac import FLAC


class LyricsManager:
    SEARCH_URL   = "https://lrclib.net/api/search"
    _cache: dict = {}
    _cache_lock  = threading.Lock()

    # Regex patterns to strip noise from video titles before searching
    _NOISE = [
        r'\(.*?(official|video|audio|mv|lyric|lyrics|visualizer|hd|4k|360|vr|live'
        r'|karaoke|cover|remix|feat|ft\.?|explicit|clean|ver\.?|version|remaster'
        r'|remastered|extended|instrumental|radio.?edit|bonus|track|album|single'
        r'|release|full|premiere|teaser|trailer|clip|short|shorts|tiktok|youtube'
        r'|music|entertainment|records|official.?video|official.?audio'
        r'|official.?mv|official.?lyric).*?\)',
        r'\[.*?(official|video|audio|mv|lyric|lyrics|visualizer|hd|4k|live'
        r'|karaoke|cover|remix|feat|ft\.?|explicit|clean|ver\.?|version|remaster'
        r'|remastered|extended|instrumental|radio.?edit|bonus|track|album|single'
        r'|release|full|premiere|teaser|trailer|clip|short|shorts|tiktok|youtube'
        r'|music|entertainment|records|official.?video|official.?audio'
        r'|official.?mv|official.?lyric).*?\]',
        r'\[.*?\]',
        r'\|.*$', r'//.*$',
        r'ft\.?\s+\S+', r'feat\.?\s+\S+', r'\s{2,}',
    ]

    # ─── Cache helpers ───────────────────────────────────────────────

    @classmethod
    def _load_cache(cls) -> None:
        """Load lyrics cache from disk. Must be called inside _cache_lock."""
        if cls._cache:
            return
        if LYRICS_CACHE.exists():
            try:
                with open(LYRICS_CACHE, "r", encoding="utf-8") as f:
                    cls._cache = json.load(f)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"Lyrics cache error: {exc}")
                cls._cache = {}

    @classmethod
    def _save_cache(cls) -> None:
        try:
            with open(LYRICS_CACHE, "w", encoding="utf-8") as f:
                json.dump(cls._cache, f, ensure_ascii=False, indent=2)
        except OSError as exc:
            logger.warning(f"Lyrics cache write: {exc}")

    @classmethod
    def _key(cls, title: str, artist: str) -> str:
        return hashlib.md5(f"{title.lower()}|{artist.lower()}".encode()).hexdigest()

    # ─── HTTP ────────────────────────────────────────────────────────

    @staticmethod
    def _http_get(url: str, params: dict):
        try:
            full = f"{url}?{urllib.parse.urlencode(params)}"
            req  = urllib.request.Request(
                full, headers={"User-Agent": f"YTDLUltimate/{VERSION}"}
            )
            with urllib.request.urlopen(req, timeout=LYRICS_HTTP_TIMEOUT) as r:
                return json.loads(r.read().decode())
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            logger.debug(f"Lyrics HTTP: {exc}")
            return None

    # ─── Title cleaning ──────────────────────────────────────────────

    @classmethod
    def _clean(cls, t: str) -> str:
        for p in cls._NOISE:
            t = re.sub(p, " ", t, flags=re.IGNORECASE)
        t = re.sub(r'[\-=_|/\\,\.]+$', '', t).strip()
        return re.sub(r'\s{2,}', ' ', t).strip()

    # ─── Result picking ──────────────────────────────────────────────

    @classmethod
    def _pick(cls, results: list, duration):
        cands = [r for r in results if (r.get("syncedLyrics") or "").strip()]
        if not cands:
            cands = [r for r in results if (r.get("plainLyrics") or "").strip()]
            return cands[0].get("plainLyrics", "").strip() if cands else None
        if duration:
            cands.sort(key=lambda r: abs((r.get("duration") or 0) - duration))
        return (cands[0].get("syncedLyrics") or cands[0].get("plainLyrics", "")).strip()

    # ─── Public fetch ────────────────────────────────────────────────

    @classmethod
    def fetch(cls, title: str, artist: str = "", duration=None):
        """Return LRC or plain-text lyrics string, or None if not found."""
        ck = cls._key(title, artist)
        # Load cache and check hit inside a single lock acquisition
        with cls._cache_lock:
            cls._load_cache()
            if ck in cls._cache:
                return cls._cache[ck]

        clean   = cls._clean(title)
        queries = []
        if artist:
            queries += [{"track_name": title, "artist_name": artist},
                        {"track_name": clean, "artist_name": artist}]
        queries.append({"track_name": clean})
        if " - " in clean:
            a, t = clean.split(" - ", 1)
            queries += [{"track_name": t.strip(), "artist_name": a.strip()},
                        {"track_name": t.strip()}]

        lrc  = None
        seen = set()
        for q in queries:
            k = str(sorted(q.items()))
            if k in seen:
                continue
            seen.add(k)
            res = cls._http_get(cls.SEARCH_URL, q) or []
            lrc = cls._pick(res, duration)
            if lrc:
                break

        with cls._cache_lock:
            cls._cache[ck] = lrc
        cls._save_cache()
        return lrc

    # ─── Artist extraction ───────────────────────────────────────────

    @staticmethod
    def _artist(info: dict) -> str:
        for f in ("artist", "creator", "album_artist", "channel", "uploader"):
            v = (info.get(f) or "").replace(" - Topic", "").strip()
            if v:
                return v
        return ""

    # ─── LRC parser for SYLT ─────────────────────────────────────────

    @staticmethod
    def _parse_lrc_for_sylt(lrc: str) -> list:
        """Parse LRC timestamp lines into SYLT-compatible (text, ms) tuples."""
        entries = []
        for line in lrc.splitlines():
            m = re.match(r'\[(\d+):(\d+)[.,](\d+)\](.*)', line)
            if m:
                mins, secs, cs, text = m.groups()
                ms = (int(mins) * 60 + int(secs)) * 1000 + int(cs.ljust(3, '0')[:3])
                entries.append((text.strip(), ms))
        return entries

    # ─── Embed: MP3 ──────────────────────────────────────────────────

    @staticmethod
    def embed_mp3(path: str, lrc: str) -> bool:
        """
        Embed lyrics into an MP3 file.
        Uses SYLT (Synchronized Lyrics) for LRC-format content,
        or USLT (Unsynchronized Lyrics) for plain text.
        """
        if not MUTAGEN_AVAILABLE:
            return False
        try:
            try:
                tags = ID3(path)
            except ID3NoHeaderError:
                tags = ID3()

            is_synced = lrc.startswith("[") and re.match(r'\[\d+:\d+', lrc)
            if is_synced:
                tags.delall("SYLT")
                parsed = LyricsManager._parse_lrc_for_sylt(lrc)
                if parsed:
                    tags.add(SYLT(encoding=Encoding.UTF8, lang="eng",
                                  format=2, type=1, text=parsed))
                else:
                    # LRC parse produced no entries — fall back to USLT
                    tags.delall("USLT")
                    tags.add(USLT(encoding=3, lang="eng", desc="", text=lrc))
            else:
                tags.delall("USLT")
                tags.add(USLT(encoding=3, lang="eng", desc="", text=lrc))

            tags.save(path, v2_version=3)
            return True
        except Exception as exc:
            logger.warning(f"embed_mp3: {exc}")
            return False

    # ─── Embed: FLAC ─────────────────────────────────────────────────

    @staticmethod
    def embed_flac(path: str, lrc: str) -> bool:
        if not MUTAGEN_AVAILABLE:
            return False
        try:
            a = FLAC(path)
            a["LYRICS"] = lrc
            a.save()
            return True
        except Exception as exc:
            logger.warning(f"embed_flac: {exc}")
            return False

    # ─── Save .lrc sidecar ───────────────────────────────────────────

    @staticmethod
    def save_lrc(audio_path: str, lrc: str):
        try:
            p = Path(audio_path).with_suffix(".lrc")
            p.write_text(lrc, encoding="utf-8")
            return str(p)
        except OSError as exc:
            logger.warning(f"save_lrc: {exc}")
            return None

    # ─── Main orchestration ──────────────────────────────────────────

    @classmethod
    def process(cls, info: dict, dest: str, fmt: str,
                embed: bool, save_file: bool) -> None:
        """
        Fetch lyrics for a downloaded track and embed or save them
        according to the caller's preferences.
        """
        # Import here to avoid circular imports at module load time
        from ytdl.ui import UI, C

        title    = info.get("title", "")
        artist   = cls._artist(info)
        duration = info.get("duration")
        vid      = info.get("id", "")
        clean    = cls._clean(title)

        UI.info(
            f"Mencari lirik  *  \"{clean[:45]}\""
            + (f"  *  {artist[:25]}" if artist else ""),
            color=C.SKY
        )

        lrc = cls.fetch(title, artist, duration)
        if not lrc:
            UI.warn("Lirik tidak ditemukan.")
            return

        label = "LRC tersinkronisasi" if lrc.startswith("[") else "Lirik teks"
        safe  = sanitize_filename(title)
        apath = Path(dest) / f"{safe} [{vid}].{fmt}"
        if not apath.exists():
            m = list(Path(dest).glob(f"*{vid}*.{fmt}"))
            if m:
                apath = m[0]

        embedded = False
        if embed and apath.exists():
            if   fmt == "mp3":  embedded = cls.embed_mp3(str(apath), lrc)
            elif fmt == "flac": embedded = cls.embed_flac(str(apath), lrc)
            else:               save_file = True

            if embedded:
                UI.ok(f"{label} ditanam ke {fmt.upper()}")
            elif not MUTAGEN_AVAILABLE and fmt in ("mp3", "flac"):
                UI.warn("Mutagen diperlukan: pip install mutagen")
            elif fmt in ("mp3", "flac"):
                save_file = True

        if save_file or (embed and not embedded):
            saved = cls.save_lrc(str(apath), lrc)
            (UI.ok(f"File LRC disimpan: {Path(saved).name}")
             if saved else UI.warn("Gagal simpan .lrc"))
