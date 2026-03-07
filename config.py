"""
config.py
=========
ConfigManager: load, validate, and persist application configuration.
Handles directory creation and optional Termux storage setup.
"""

import os
import json
import subprocess
import logging
from pathlib import Path

from ytdl.constants import (
    CONFIG_FILE, DEFAULT_CONFIG,
    AUDIO_FORMATS, VALID_VIDEO_RESOLUTIONS, VALID_AUDIO_QUALITIES,
)

logger = logging.getLogger("ytdl")


class ConfigManager:
    def __init__(self):
        self.config = self._load()
        self._ensure_dirs()

    # ─── Load / Save ─────────────────────────────────────────────────

    def _load(self) -> dict:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return self._validate({**DEFAULT_CONFIG, **data})
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning(f"Config load error: {exc}")
        return DEFAULT_CONFIG.copy()

    def save(self) -> None:
        # Import here to avoid circular import (UI → constants, config → UI)
        from ytdl.ui import UI
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4, ensure_ascii=False)
        except OSError as exc:
            UI.err(f"Gagal menyimpan config: {exc}")

    # ─── Validation ──────────────────────────────────────────────────

    def _validate(self, cfg: dict) -> dict:
        def reset(k):
            cfg[k] = DEFAULT_CONFIG[k]

        if cfg.get("audio_format") not in AUDIO_FORMATS:
            reset("audio_format")
        if cfg.get("video_resolution") not in VALID_VIDEO_RESOLUTIONS:
            reset("video_resolution")
        if str(cfg.get("audio_quality", "")) not in VALID_AUDIO_QUALITIES:
            reset("audio_quality")
        try:
            n = int(cfg.get("max_connections", 10))
            cfg["max_connections"] = n if 1 <= n <= 32 else 10
        except (ValueError, TypeError):
            reset("max_connections")
        for flag in ("use_aria2c", "embed_thumbnail", "embed_metadata",
                     "embed_subs", "embed_chat", "embed_lyrics", "save_lrc_file"):
            if not isinstance(cfg.get(flag), bool):
                cfg[flag] = bool(DEFAULT_CONFIG.get(flag, False))
        for k in ("path_video", "path_audio"):
            if not isinstance(cfg.get(k), str) or not cfg[k].strip():
                reset(k)
        return cfg

    # ─── Directory setup ─────────────────────────────────────────────

    def _ensure_dirs(self) -> None:
        from ytdl.ui import UI
        if not os.path.exists("/sdcard"):
            try:
                subprocess.run(
                    ["termux-setup-storage"], check=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                    timeout=15
                )
            except (subprocess.CalledProcessError, FileNotFoundError,
                    subprocess.TimeoutExpired):
                pass
        for k in ("path_video", "path_audio"):
            try:
                Path(self.config[k]).mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                UI.err(f"mkdir '{self.config[k]}': {exc}")
