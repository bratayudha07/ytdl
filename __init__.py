"""
ytdl — YouTube Ultimate Downloader Pro v4.1.0
=============================================
Package structure:

    constants.py  — logging, dependency checks, all app-wide constants
    utils.py      — sanitize_filename, validate_url, exponential_backoff
    ui.py         — C (colors), G (glyphs), Layout, UI, Spinner
    lyrics.py     — LyricsManager (fetch, embed, save .lrc)
    config.py     — ConfigManager (load, validate, persist)
    history.py    — HistoryManager (append-only, thread-safe)
    engine.py     — Engine (download, download_playlist)
    settings.py   — SettingsMenu, pick_quality
    main.py       — App (main loop) + entry point

Usage:
    python -m ytdl.main
    # or directly:
    python ytdl/main.py
"""
