"""
ui.py
=====
Terminal design system: ANSI color palette (C), glyph set (G),
layout utilities (Layout), stateless output methods (UI),
and the threaded loading Spinner.
"""

import os
import sys
import time
import logging
import threading

from ytdl.constants import (
    APP_NAME, VERSION, TAGLINE,
    FFMPEG_AVAILABLE, MUTAGEN_AVAILABLE,
)

logger = logging.getLogger("ytdl")

# ───────────────────────────────────────────────────────────────────
# Python < 3.12 compatibility: define Unicode chars outside f-strings
# ───────────────────────────────────────────────────────────────────
_HL  = '\u2500'   # ─  horizontal line


# =======================================================================
# DESIGN SYSTEM — Color palette + Glyphs + Layout
# =======================================================================

class C:
    """ANSI color palette — dark luxury theme."""
    RST   = '\033[0m'
    BOLD  = '\033[1m'
    DIM   = '\033[2m'

    GOLD  = '\033[38;5;220m'    # Primary accent
    AMBER = '\033[38;5;214m'    # Secondary accent
    CREAM = '\033[38;5;230m'    # Main text
    STONE = '\033[38;5;244m'    # Muted text
    SMOKE = '\033[38;5;238m'    # Borders / very muted

    JADE  = '\033[38;5;78m'     # Success
    ROSE  = '\033[38;5;204m'    # Error
    MAIZE = '\033[38;5;227m'    # Warning
    SKY   = '\033[38;5;117m'    # Info

    BAR_FILL  = '\033[38;5;220m'
    BAR_EMPTY = '\033[38;5;237m'


class G:
    """Glyph set."""
    # Box drawing
    TL = '┌'; TR = '┐'; BL = '└'; BR = '┘'
    H  = '─';  V  = '│'
    # Icons
    OK    = '[OK]'
    FAIL  = '[!!]'
    WARN  = '[!]'
    ARROW = '>'
    DOT   = '*'
    STAR  = '**'
    MUSIC = '[M]'
    VIDEO = '[V]'
    GEAR  = '[S]'
    HIST  = '[H]'
    LOG_I = '[L]'
    EXIT  = '[X]'
    # Progress
    PB_FULL  = '#'
    PB_HALF  = '='
    PB_EMPTY = '-'


def _tw() -> int:
    """Return terminal width, capped at 80 columns."""
    try:
        return min(os.get_terminal_size().columns, 80)
    except OSError:
        return 72


class Layout:
    @staticmethod
    def hline(color: str = C.SMOKE) -> str:
        return f"{color}{'-' * _tw()}{C.RST}"

    @staticmethod
    def section_rule(label: str = "", color: str = C.SMOKE,
                     label_color: str = C.STONE) -> str:
        w = _tw() - 2
        if label:
            pad  = w - len(label) - 2
            left = pad // 2
            rght = pad - left
            return (f"{color}{'-' * left}{C.RST} "
                    f"{label_color}{C.DIM}{label}{C.RST} "
                    f"{color}{_HL * rght}{C.RST}")
        return f"{color}{_HL * w}{C.RST}"


# =======================================================================
# UI — Stateless output methods
# =======================================================================

class UI:
    _spinner_hooks: list = []

    @classmethod
    def register_spinner_hook(cls, fn) -> None:
        cls._spinner_hooks.append(fn)

    @staticmethod
    def banner() -> None:
        os.system('clear' if os.name != 'nt' else 'cls')
        w = _tw()

        print(f"\n{C.SMOKE}{_HL * w}{C.RST}")
        print(f"  {C.GOLD}{C.BOLD}{APP_NAME}{C.RST}")
        print(f"  {C.STONE}{C.DIM}v{VERSION}  *  {TAGLINE}{C.RST}")

        ffmpeg_chip = (f"{C.JADE}  ffmpeg OK  {C.RST}" if FFMPEG_AVAILABLE
                       else f"{C.ROSE}  ffmpeg MISSING  {C.RST}")
        mutag_chip  = (f"{C.JADE}  mutagen OK  {C.RST}" if MUTAGEN_AVAILABLE
                       else f"{C.STONE}  mutagen --  {C.RST}")
        print(f"\n  {ffmpeg_chip}   {mutag_chip}")
        print(f"{C.SMOKE}{_HL * w}{C.RST}\n")

    @staticmethod
    def ok(text: str) -> None:
        print(f"  {C.JADE}OK{C.RST}   {C.CREAM}{text}{C.RST}")
        logger.info(text)

    @staticmethod
    def err(text: str) -> None:
        print(f"  {C.ROSE}!!{C.RST}   {C.ROSE}{text}{C.RST}")
        logger.error(text)

    @staticmethod
    def warn(text: str) -> None:
        print(f"  {C.MAIZE}! {C.RST}   {C.MAIZE}{text}{C.RST}")
        logger.warning(text)

    @staticmethod
    def info(text: str, color: str = C.SKY) -> None:
        print(f"  {color}>{C.RST}   {C.CREAM}{text}{C.RST}")

    @staticmethod
    def label(key: str, value: str) -> None:
        print(f"  {C.STONE}{key:<14}{C.RST}  {C.CREAM}{value}{C.RST}")

    @staticmethod
    def rule(label: str = "") -> None:
        print(f"\n  {Layout.section_rule(label)}\n")

    @staticmethod
    def gap(n: int = 1) -> None:
        print("\n" * (n - 1))

    @staticmethod
    def ask(prompt: str) -> str:
        try:
            return input(
                f"  {C.GOLD}>{C.RST}  {C.CREAM}{C.BOLD}{prompt}{C.RST}  "
            ).strip()
        except EOFError:
            return ""

    @classmethod
    def _fire_spinner_stop(cls) -> None:
        for fn in cls._spinner_hooks:
            fn()

    @classmethod
    def progress_hook(cls, d: dict) -> None:
        """yt-dlp progress hook."""
        if d["status"] == "downloading":
            try:
                cls._fire_spinner_stop()
                raw   = d.get("_percent_str", "0%").replace("%", "").strip()
                pct   = float(raw) if raw not in ("N/A", "") else 0.0
                speed = d.get("_speed_str", "--")
                eta   = d.get("_eta_str", "--")
                size  = d.get("_total_bytes_str") or d.get("_total_bytes_estimate_str", "--")

                filled = int(28 * pct / 100)
                bar    = (f"{C.BAR_FILL}{'#' * filled}{C.RST}"
                          f"{C.BAR_EMPTY}{'-' * (28 - filled)}{C.RST}")
                pct_s  = f"{C.GOLD}{C.BOLD}{pct:5.1f}%{C.RST}"
                meta   = f"{C.STONE}{speed}  *  ETA {eta}  *  {size}{C.RST}"

                sys.stdout.write(f"\r  [{bar}]  {pct_s}  {meta}   ")
                sys.stdout.flush()
            except (ValueError, TypeError) as exc:
                logger.debug(f"Progress parse: {exc}")

        elif d["status"] == "finished":
            sys.stdout.write(f"\r{' ' * 80}\r")
            sys.stdout.flush()
            UI.ok("Transfer selesai -- memproses file...")


# =======================================================================
# SPINNER
# =======================================================================

class Spinner:
    _lock:   threading.Lock = threading.Lock()
    _active: object         = None
    FRAMES = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]

    def __init__(self, label: str = "Memproses"):
        self._label      = label
        self._stop_event = threading.Event()
        self._thread     = threading.Thread(target=self._loop, daemon=True)

    def _loop(self) -> None:
        i = 0
        while not self._stop_event.is_set():
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(
                f"\r  {C.GOLD}{frame}{C.RST}  {C.STONE}{self._label}...{C.RST}   "
            )
            sys.stdout.flush()
            time.sleep(0.12)
            i += 1
        sys.stdout.write(f"\r{' ' * (len(self._label) + 24)}\r")
        sys.stdout.flush()

    def start(self) -> "Spinner":
        with Spinner._lock:
            Spinner._active = self
        self._thread.start()
        return self

    def stop(self) -> None:
        self._stop_event.set()
        self._thread.join(timeout=1)
        with Spinner._lock:
            if Spinner._active is self:
                Spinner._active = None

    @classmethod
    def stop_global(cls) -> None:
        with cls._lock:
            active = cls._active
        if active:
            active.stop()


# Register Spinner as a UI spinner hook so progress_hook can stop it
UI.register_spinner_hook(Spinner.stop_global)
