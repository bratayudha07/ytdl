"""
history.py
==========
HistoryManager: thread-safe append-only download history,
persisted as a JSON file, with a simple terminal display.
"""

import json
import logging
import threading
from datetime import datetime

from ytdl.constants import HISTORY_FILE

logger = logging.getLogger("ytdl")


class HistoryManager:
    MAX = 1000   # maximum entries retained in memory and on disk

    def __init__(self):
        self._lock = threading.Lock()
        self.data  = self._load()

    # ─── Persistence ─────────────────────────────────────────────────

    def _load(self) -> list:
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    return d if isinstance(d, list) else []
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"History load: {exc}")
        return []

    def add(self, entry: dict) -> None:
        with self._lock:
            self.data.append(
                {**entry, "ts": datetime.now().strftime("%Y-%m-%d %H:%M")}
            )
            if len(self.data) > self.MAX:
                self.data = self.data[-self.MAX:]
            try:
                with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
            except OSError as exc:
                logger.warning(f"History write: {exc}")

    # ─── Display ─────────────────────────────────────────────────────

    def show(self, limit: int = 20) -> None:
        from ytdl.ui import UI, C
        UI.banner()
        UI.rule("Riwayat Download")
        if not self.data:
            UI.warn("Belum ada riwayat.")
            return
        for entry in reversed(self.data[-limit:]):
            ts    = entry.get("ts", "")[:16]
            title = entry.get("title", "--")[:52]
            mode  = entry.get("mode", "?").upper()
            icon  = "[M]" if mode == "AUDIO" else "[V]"
            print(f"  {C.STONE}{ts}{C.RST}  {C.GOLD}{icon}{C.RST}  {C.CREAM}{title}{C.RST}")
        UI.gap()
