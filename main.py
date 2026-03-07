"""
main.py
=======
App: the main application loop — renders the menu, dispatches
user input to Engine / SettingsMenu / HistoryManager, and
installs a SIGINT handler for graceful cancellation.

Entry point: run  python -m ytdl  or  python ytdl/main.py
"""

import sys
import time
import signal
import logging

from ytdl.constants import LOG_FILE
from ytdl.utils     import validate_url
from ytdl.ui        import UI, C, Spinner, _HL, _tw
from ytdl.config    import ConfigManager
from ytdl.history   import HistoryManager
from ytdl.engine    import Engine
from ytdl.settings  import SettingsMenu

logger = logging.getLogger("ytdl")


class App:
    MENU = [
        ("1",  "[M]", "Download Audio         MP3 / FLAC / WAV / Opus / M4A"),
        ("2",  "[V]", "Download Video         MP4 / MKV / WebM"),
        ("3",  "[M]", "Download Playlist Audio"),
        ("4",  "[V]", "Download Playlist Video"),
        ("--", "",    ""),
        ("5",  "[S]", "Pengaturan"),
        ("6",  "[H]", "Riwayat Download"),
        ("7",  "[L]", "Lihat Log Debug"),
        ("--", "",    ""),
        ("0",  "[X]", "Keluar"),
    ]

    def __init__(self):
        self.cfg      = ConfigManager()
        self.hist     = HistoryManager()
        self.engine   = Engine(self.cfg, self.hist)
        self.settings = SettingsMenu(self.cfg)
        self._signals()

    # ─── Signal handling ─────────────────────────────────────────────

    def _signals(self) -> None:
        def _handler(sig, frame):
            Spinner.stop_global()
            print(f"\n\n  {C.MAIZE}! Dibatalkan.{C.RST}\n")
            sys.exit(0)
        signal.signal(signal.SIGINT, _handler)

    # ─── Input helpers ───────────────────────────────────────────────

    def _get_url(self):
        url = UI.ask("URL YouTube")
        if not validate_url(url):
            UI.err("URL tidak valid  --  harus dimulai dengan https://")
            time.sleep(1.2)
            return None
        return url

    def _pause(self) -> None:
        input(f"\n  {C.STONE}Tekan Enter untuk kembali...{C.RST}")

    # ─── Main loop ───────────────────────────────────────────────────

    def run(self) -> None:
        while True:
            UI.banner()

            for key, icon, label in self.MENU:
                if key == "--":
                    print(f"  {C.SMOKE}{_HL * (_tw() - 4)}{C.RST}")
                    continue
                k_s = f"{C.GOLD}{C.BOLD}{key:>2}{C.RST}"
                i_s = f"{C.AMBER}{icon}{C.RST}" if icon else "    "
                l_s = f"{C.CREAM}{label}{C.RST}"
                print(f"  {k_s}  {i_s}  {l_s}")

            UI.gap()
            choice = UI.ask("Pilihan")

            if choice == "0":
                print(f"\n  {C.GOLD}**  Sampai jumpa.{C.RST}\n")
                sys.exit(0)

            elif choice == "1":
                url = self._get_url()
                if url:
                    fmt  = self.cfg.config.get("audio_format", "mp3").upper()
                    qlty = self.cfg.config.get("audio_quality", "192")
                    UI.gap()
                    UI.info(f"Format: {fmt}  *  {qlty} kbps", color=C.GOLD)
                    self.engine.download(url, "audio")
                    self._pause()

            elif choice == "2":
                url = self._get_url()
                if url:
                    self.engine.download(url, "video")
                    self._pause()

            elif choice == "3":
                url = self._get_url()
                if url:
                    self.engine.download_playlist(url, "audio")
                    self._pause()

            elif choice == "4":
                url = self._get_url()
                if url:
                    self.engine.download_playlist(url, "video")
                    self._pause()

            elif choice == "5":
                self.settings.show()

            elif choice == "6":
                self.hist.show()
                self._pause()

            elif choice == "7":
                UI.banner()
                UI.rule("Log Debug")
                try:
                    lines = LOG_FILE.read_text(encoding="utf-8").splitlines()
                    for ln in lines[-40:]:
                        ts   = ln[:23] if len(ln) > 23 else ln
                        rest = ln[24:] if len(ln) > 24 else ""
                        print(f"  {C.STONE}{ts}{C.RST}  {C.DIM}{rest}{C.RST}")
                except OSError:
                    UI.warn("Log belum tersedia.")
                self._pause()

            else:
                UI.warn("Pilihan tidak dikenal.")
                time.sleep(0.8)


# =======================================================================
# ENTRY POINT
# =======================================================================

if __name__ == "__main__":
    App().run()
