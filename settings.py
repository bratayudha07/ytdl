"""
settings.py
===========
SettingsMenu: interactive terminal menu for editing configuration.
Video quality is configured as a resolution preference (max/1080/720/480/360)
and stored in config so no per-download prompt is needed.
"""

import time
import logging

from ytdl.constants import (
    AUDIO_FORMATS, VALID_VIDEO_RESOLUTIONS, VALID_AUDIO_QUALITIES,
)

logger = logging.getLogger("ytdl")

# Ordered list used when rendering the resolution submenu
_RES_KEYS = ["max", "1080", "720", "480", "360"]


class SettingsMenu:
    def __init__(self, cfg):
        self.cfg = cfg

    def show(self) -> None:
        from ytdl.ui import UI, C
        while True:
            UI.banner()
            c = self.cfg.config
            UI.rule("Konfigurasi")

            res_val   = c.get("video_resolution", "1080")
            res_label = VALID_VIDEO_RESOLUTIONS.get(res_val, res_val).strip()

            rows = [
                ("1",  "path_video",       c["path_video"],           "Path Video"),
                ("2",  "path_audio",       c["path_audio"],           "Path Audio"),
                ("3",  "video_resolution", res_label,                 "Resolusi Video"),
                ("4",  "audio_format",
                 f"{c['audio_format'].upper()}  *  {AUDIO_FORMATS[c['audio_format']][0]}",
                 "Format Audio"),
                ("5",  "audio_quality",    f"{c['audio_quality']} kbps", "Kualitas Audio"),
                ("6",  "use_aria2c",        "Ya" if c["use_aria2c"]       else "Tidak", "Aria2c"),
                ("7",  "max_connections",   str(c["max_connections"]),     "Max Koneksi"),
                ("8",  "embed_thumbnail",   "Ya" if c["embed_thumbnail"]  else "Tidak", "Thumbnail"),
                ("9",  "embed_subs",        "Ya" if c["embed_subs"]       else "Tidak", "Subtitel"),
                ("10", "embed_lyrics",      "Ya" if c["embed_lyrics"]     else "Tidak", "Embed Lirik"),
                ("11", "save_lrc_file",     "Ya" if c["save_lrc_file"]    else "Tidak", "Simpan .lrc"),
            ]
            for num, _, val, label in rows:
                num_s   = f"{C.GOLD}{C.BOLD}{num:>3}{C.RST}"
                label_s = f"{C.STONE}{label:<16}{C.RST}"
                val_s   = f"{C.CREAM}{val}{C.RST}"
                print(f"  {num_s}  {label_s}  {val_s}")

            UI.gap()
            print(f"  {C.STONE}  0  Kembali{C.RST}")
            UI.rule()

            choice = UI.ask("Nomor setting")
            if choice == "0":
                break
            self._edit(choice, {r[0]: r for r in rows})

    def _edit(self, choice: str, rows: dict) -> None:
        from ytdl.ui import UI, C
        if choice not in rows:
            UI.warn("Pilihan tidak valid.")
            return
        num, key, _, label = rows[choice]

        # Resolution uses a numbered submenu instead of free-text input
        if key == "video_resolution":
            self._edit_resolution()
            return

        BOOL_KEYS = {"use_aria2c", "embed_thumbnail", "embed_metadata",
                     "embed_subs", "embed_chat", "embed_lyrics", "save_lrc_file"}
        INT_KEYS  = {"max_connections"}
        hints = {
            "audio_format":  f"Pilihan: {', '.join(AUDIO_FORMATS)}",
            "audio_quality": f"Pilihan: {', '.join(sorted(VALID_AUDIO_QUALITIES, key=int))} kbps",
        }
        hint = hints.get(key, "")
        if hint:
            UI.info(hint, color=C.STONE)

        val_raw = UI.ask(f"Nilai baru untuk {label}")
        if not val_raw:
            return

        try:
            if key in BOOL_KEYS:
                val = val_raw.lower() in ("y", "ya", "yes", "1", "true")
            elif key in INT_KEYS:
                val = int(val_raw)
            else:
                val = val_raw

            validated = self.cfg._validate({**self.cfg.config, key: val})
            self.cfg.config = validated
            self.cfg.save()
            UI.ok(f"{label} diperbarui.")
        except (ValueError, TypeError) as exc:
            UI.warn(f"Nilai tidak valid: {exc}")

        time.sleep(0.8)

    def _edit_resolution(self) -> None:
        """Show a numbered submenu for selecting the default video resolution."""
        from ytdl.ui import UI, C
        UI.gap()
        UI.rule("Resolusi Video")
        for i, key in enumerate(_RES_KEYS, start=1):
            label = VALID_VIDEO_RESOLUTIONS[key]
            k_s   = f"{C.GOLD}{C.BOLD}{i}{C.RST}"
            l_s   = f"{C.CREAM}{label}{C.RST}"
            print(f"  {k_s}  {l_s}")
        UI.gap()

        choice = UI.ask("Pilih resolusi")
        idx    = int(choice) - 1 if choice.isdigit() else -1
        if 0 <= idx < len(_RES_KEYS):
            new_val   = _RES_KEYS[idx]
            validated = self.cfg._validate({**self.cfg.config, "video_resolution": new_val})
            self.cfg.config = validated
            self.cfg.save()
            UI.ok(f"Resolusi Video diperbarui: {VALID_VIDEO_RESOLUTIONS[new_val].strip()}")
        else:
            UI.warn("Pilihan tidak valid.")

        time.sleep(0.8)
