"""
engine.py
=========
Engine: the download core.
Builds yt-dlp command arguments, fetches metadata,
drives single-track and parallel playlist downloads with retries.
"""

import re
import sys
import json
import shutil
import logging
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from ytdl.constants import (
    AUDIO_FORMATS, COOKIE_FILE,
    SOCKET_TIMEOUT, META_TIMEOUT, DL_TIMEOUT,
    MAX_RETRIES, MAX_PLAYLIST_WORKERS,
)
from ytdl.utils import validate_url, exponential_backoff

logger = logging.getLogger("ytdl")


class Engine:
    def __init__(self, cfg, hist):
        self.cfg  = cfg
        self.hist = hist

    # ─── Argument builder ────────────────────────────────────────────

    def _args(self, mode: str, quality: str, playlist: bool, dest: str) -> list:
        from ytdl.ui import UI, C
        c        = self.cfg.config
        a        = [sys.executable, "-m", "yt_dlp"]
        fmt      = c.get("audio_format", "mp3")
        lossless = AUDIO_FORMATS.get(fmt, ("", False))[1]

        if mode == "audio":
            sel = ("bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio[ext=opus]"
                   "/bestaudio/best[ext=webm]/best[ext=m4a]/best")
            a += ["-f", sel, "-x", "--audio-format", fmt]
            if not lossless:
                # Apply quality setting for all lossy formats (mp3, opus, m4a)
                a += ["--audio-quality", c.get("audio_quality", "192")]
        else:
            quality = c.get("video_resolution", "1080")
            if quality == "max":
                a += ["-f", "bestvideo+bestaudio/best"]
            else:
                a += ["-f",
                      f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]/best"]

        a += ["-o", f"{dest}/%(title)s [%(id)s].%(ext)s"]
        if mode == "video":
            a += ["--merge-output-format", "mp4"]

        if c.get("embed_thumbnail"): a += ["--embed-thumbnail"]
        if c.get("embed_metadata"):  a += ["--embed-metadata", "--add-chapters"]
        if mode == "video" and c.get("embed_subs"):
            a += ["--embed-subs", "--write-subs"]

        a += [
            "--socket-timeout",   str(SOCKET_TIMEOUT),
            "--no-check-certificates",
            "--extractor-args",   "youtube:player_client=web,mweb,-android_vr",
            "--retries",          str(MAX_RETRIES),
            "--fragment-retries", str(MAX_RETRIES),
        ]
        if not playlist:
            a += ["--no-playlist"]

        if c.get("use_aria2c") and shutil.which("aria2c") and not lossless:
            n = str(c.get("max_connections", 10))
            a += ["--downloader", "aria2c",
                  "--downloader-args", f"aria2c:-x {n} -s {n} -k 1M"]
        elif c.get("use_aria2c") and lossless:
            UI.warn("Aria2c dinonaktifkan untuk mode lossless.")

        if COOKIE_FILE.exists():
            a += ["--cookies", str(COOKIE_FILE)]

        a += ["--ignore-errors", "--progress", "--newline"]
        return a

    # ─── Metadata fetcher ────────────────────────────────────────────

    def _meta(self, url: str):
        from ytdl.ui import UI
        base = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json", "--no-playlist",
            "--socket-timeout", str(SOCKET_TIMEOUT),
            "--no-check-certificates",
            "--ignore-errors",
        ]
        if COOKIE_FILE.exists():
            base += ["--cookies", str(COOKIE_FILE)]

        variants = [
            ["--extractor-args", "youtube:player_client=default,-android_vr"],
            ["--extractor-args", "youtube:player_client=web,mweb"],
        ]
        for v in variants:
            proc = None
            try:
                proc = subprocess.Popen(
                    base + v + [url],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
                )
                out, err = proc.communicate(timeout=META_TIMEOUT)
                if proc.returncode != 0:
                    logger.debug(f"meta stderr: {err[:200]}")
                    continue
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("{"):
                        try:
                            return json.loads(line)
                        except json.JSONDecodeError:
                            continue
            except subprocess.TimeoutExpired:
                UI.warn("Timeout metadata -- mencoba variasi berikutnya...")
            except OSError as exc:
                UI.err(f"OS error metadata: {exc}")
                break
            finally:
                if proc and proc.poll() is None:
                    try:
                        proc.kill(); proc.wait(timeout=5)
                    except OSError:
                        pass
        return None

    # ─── Single download ─────────────────────────────────────────────

    def download(self, url: str, mode: str) -> bool:
        from ytdl.ui import UI, Spinner, C
        from ytdl.lyrics import LyricsManager

        if not validate_url(url):
            UI.err(f"URL tidak valid: {url}")
            return False

        c    = self.cfg.config
        dest = c["path_audio"] if mode == "audio" else c["path_video"]

        sp   = Spinner("Mengambil metadata").start()
        info = self._meta(url)
        sp.stop()

        if not info:
            UI.err("Gagal mengambil metadata. Periksa URL atau koneksi.")
            return False

        title    = info.get("title", url)
        duration = info.get("duration_string", "--")

        UI.gap()
        UI.rule()
        UI.label("Judul",   title[:60])
        UI.label("Durasi",  duration)
        UI.label("Mode",    mode.upper())
        if mode == "audio":
            UI.label("Format",
                     c.get("audio_format", "mp3").upper()
                     + f"  *  {c.get('audio_quality', '--')} kbps")
        else:
            from ytdl.constants import VALID_VIDEO_RESOLUTIONS
            res = c.get("video_resolution", "1080")
            UI.label("Resolusi", VALID_VIDEO_RESOLUTIONS.get(res, res).strip())
        UI.rule()

        args    = self._args(mode, "", False, dest) + [url]
        success = False

        for attempt in range(MAX_RETRIES):
            if attempt > 0:
                UI.warn(f"Retry {attempt + 1}/{MAX_RETRIES}...")
                exponential_backoff(attempt)

            proc = None
            try:
                proc = subprocess.Popen(
                    args,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, bufsize=1
                )
                for line in proc.stdout:
                    line = line.rstrip()
                    if "[download]" in line and "%" in line:
                        self._render_progress(line)
                    elif "[error]" in line.lower():
                        logger.warning(f"yt-dlp: {line}")
                proc.wait(timeout=DL_TIMEOUT)
                if proc.returncode == 0:
                    success = True
                    break
                logger.warning(f"yt-dlp exit {proc.returncode}")
            except subprocess.TimeoutExpired:
                UI.warn("Download timeout!")
            except OSError as exc:
                UI.err(f"OS error: {exc}")
                break
            finally:
                if proc and proc.poll() is None:
                    try:
                        proc.kill(); proc.wait(timeout=5)
                    except OSError:
                        pass

        UI.gap()
        if success:
            UI.ok(f"Download selesai  *  {title[:50]}")
            if mode == "audio" and c.get("embed_lyrics"):
                LyricsManager.process(
                    info, dest, c.get("audio_format", "mp3"),
                    embed=True, save_file=c.get("save_lrc_file", False)
                )
            self.hist.add({"title": title, "url": url, "mode": mode})
        else:
            UI.err(f"Download gagal setelah {MAX_RETRIES} percobaan.")

        return success

    # ─── Playlist download ───────────────────────────────────────────

    def download_playlist(self, url: str, mode: str) -> None:
        from ytdl.ui import UI, Spinner, C

        if not validate_url(url):
            UI.err("URL playlist tidak valid.")
            return

        c    = self.cfg.config
        dest = c["path_audio"] if mode == "audio" else c["path_video"]

        sp  = Spinner("Mengambil daftar playlist").start()
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--flat-playlist", "--dump-json",
            "--socket-timeout", str(SOCKET_TIMEOUT),
            "--no-check-certificates",
            "--ignore-errors", url
        ]
        if COOKIE_FILE.exists():
            cmd += ["--cookies", str(COOKIE_FILE)]

        entries = []
        proc    = None
        try:
            proc = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
            )
            out, _ = proc.communicate(timeout=META_TIMEOUT)
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        e  = json.loads(line)
                        eu = e.get("url") or e.get("webpage_url")
                        if eu:
                            entries.append((e.get("title", eu), eu))
                    except json.JSONDecodeError:
                        continue
        except subprocess.TimeoutExpired:
            UI.warn("Timeout daftar playlist.")
        except OSError as exc:
            UI.err(f"OS error playlist: {exc}")
        finally:
            sp.stop()
            if proc and proc.poll() is None:
                try:
                    proc.kill(); proc.wait(timeout=5)
                except OSError:
                    pass

        if not entries:
            UI.warn("Tidak ada item di playlist.")
            return

        total = len(entries)
        UI.gap()
        UI.rule()
        UI.label("Playlist", f"{total} item  *  {MAX_PLAYLIST_WORKERS} paralel")
        UI.rule()

        ok_n = 0; fail_n = 0
        lock = threading.Lock()

        def _worker(idx: int, title: str, eu: str) -> bool:
            nonlocal ok_n, fail_n
            print(f"\n  {C.STONE}[{idx + 1}/{total}]{C.RST}  {C.CREAM}{title[:55]}{C.RST}")
            result = self.download(eu, mode)
            # Update counters inside the worker so the outer except block
            # only increments fail_n for unexpected exceptions, not double-counts.
            with lock:
                if result: ok_n  += 1
                else:      fail_n += 1
            return result

        with ThreadPoolExecutor(max_workers=MAX_PLAYLIST_WORKERS) as ex:
            futs = {ex.submit(_worker, i, t, u): (i, t)
                    for i, (t, u) in enumerate(entries)}
            for fut in as_completed(futs):
                try:
                    fut.result()
                except Exception as exc:
                    # Only reached if _worker raised an unexpected exception
                    # (download() returned False is handled inside _worker above)
                    idx, t = futs[fut]
                    logger.error(f"Worker [{t}]: {exc}")
                    with lock:
                        fail_n += 1

        UI.gap()
        UI.rule()
        UI.ok(f"Playlist selesai  *  {ok_n} berhasil  *  {fail_n} gagal")
        UI.rule()

    # ─── Progress renderer ───────────────────────────────────────────

    @staticmethod
    def _render_progress(line: str) -> None:
        import sys
        from ytdl.ui import C
        try:
            pm = re.search(r'([\d.]+)%', line)
            sm = re.search(r'at\s+([\S]+/s)', line)
            em = re.search(r'ETA\s+([\d:]+)', line)
            pct   = float(pm.group(1)) if pm else 0.0
            speed = sm.group(1)        if sm else "--"
            eta   = em.group(1)        if em else "--"

            filled = int(28 * pct / 100)
            bar    = (f"{C.BAR_FILL}{'█' * filled}{C.RST}"
                      f"{C.BAR_EMPTY}{'░' * (28 - filled)}{C.RST}")
            pct_s  = f"{C.GOLD}{C.BOLD}{pct:5.1f}%{C.RST}"
            meta   = f"{C.STONE}{speed}  *  ETA {eta}{C.RST}"

            sys.stdout.write(f"\r  [{bar}]  {pct_s}  {meta}   ")
            sys.stdout.flush()
        except (ValueError, AttributeError):
            pass
