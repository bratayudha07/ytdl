# YouTube Ultimate Downloader Pro

**v4.1.0 · Elegant. Stable. Powerful.**

Downloader YouTube berbasis terminal dengan tampilan dark-luxury, mendukung download audio/video tunggal maupun playlist secara paralel, embed lirik tersinkronisasi, dan konfigurasi lengkap yang tersimpan persisten.

---

## Fitur Utama

- **Download Audio** — MP3, FLAC, WAV, Opus, M4A dengan kontrol kualitas bitrate
- **Download Video** — MP4 (Full HD hingga 360p, atau resolusi tertinggi)
- **Playlist Paralel** — hingga 3 item diunduh sekaligus menggunakan thread pool
- **Embed Lirik Otomatis** — fetch dari lrclib.net, embed sebagai SYLT (tersinkronisasi) atau USLT (teks biasa) ke MP3; tag `LYRICS` ke FLAC; atau simpan sidecar `.lrc`
- **Retry + Exponential Backoff** — hingga 5 percobaan ulang otomatis per item
- **Aria2c Multi-koneksi** — akselerasi download dengan hingga 32 koneksi paralel (opsional)
- **Konfigurasi Persisten** — semua preferensi disimpan di `~/.ytdl_ultimate/config.json`
- **Riwayat Download** — 1000 entri terakhir, tersimpan otomatis
- **Log Debug** — dapat dilihat langsung dari menu tanpa keluar aplikasi
- **Kompatibel Android (Termux)** — otomatis mendeteksi `/sdcard` dan menjalankan `termux-setup-storage`

---

## Persyaratan

| Dependensi | Keterangan |
|---|---|
| Python ≥ 3.8 | Wajib |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | Wajib — engine download utama |
| [ffmpeg](https://ffmpeg.org) | Wajib untuk konversi audio & merge video |
| [mutagen](https://mutagen.readthedocs.io) | Opsional — untuk embed lirik ke MP3/FLAC |
| [aria2c](https://aria2.github.io) | Opsional — akselerasi multi-koneksi |

> **Catatan Python < 3.12:** kode ini kompatibel penuh dengan Python 3.8+ karena semua karakter Unicode didefinisikan di luar ekspresi f-string.

---

## Instalasi

### 1. Clone atau salin folder `ytdl/`

```
proyek-kamu/
└── ytdl/
    ├── __init__.py
    ├── constants.py
    ├── utils.py
    ├── ui.py
    ├── lyrics.py
    ├── config.py
    ├── history.py
    ├── engine.py
    ├── settings.py
    └── main.py
```

### 2. Install dependensi Python

```bash
pip install yt-dlp mutagen
```

### 3. Install ffmpeg

**Linux / Termux:**
```bash
# Debian/Ubuntu
sudo apt install ffmpeg

# Termux
pkg install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download dari [ffmpeg.org](https://ffmpeg.org/download.html) dan tambahkan ke PATH.

### 4. (Opsional) Install aria2c untuk download lebih cepat

```bash
# Debian/Ubuntu
sudo apt install aria2

# Termux
pkg install aria2

# macOS
brew install aria2
```

---

## Menjalankan

```bash
# Dari direktori induk folder ytdl/
python -m ytdl.main

# Atau langsung
python ytdl/main.py
```

---

## Penggunaan

Saat dijalankan, aplikasi menampilkan menu utama interaktif:

```
──────────────────────────────────────────────────────────────────────────────
  YouTube Ultimate Downloader
  v4.1.0  *  Elegant. Stable. Powerful.

    ffmpeg OK      mutagen OK
──────────────────────────────────────────────────────────────────────────────

   1  [M]  Download Audio         MP3 / FLAC / WAV / Opus / M4A
   2  [V]  Download Video         MP4 (resolusi dari pengaturan)
   3  [M]  Download Playlist Audio
   4  [V]  Download Playlist Video
  ──────────────────────────────────────────────────────────────────────────
   5  [S]  Pengaturan
   6  [H]  Riwayat Download
   7  [L]  Lihat Log Debug
  ──────────────────────────────────────────────────────────────────────────
   0  [X]  Keluar
```

Masukkan nomor pilihan, lalu tempel URL YouTube saat diminta.

### Download Audio (1)
Mengunduh audio dari URL, mengkonversi ke format yang dikonfigurasi, lalu secara otomatis mencari dan menanam lirik jika `embed_lyrics` aktif.

### Download Video (2)
Mengunduh video pada resolusi yang sudah dipilih di Pengaturan (default: 1080p), digabung menjadi file MP4.

### Download Playlist (3 dan 4)
Mengambil daftar semua item dari playlist, lalu mengunduh hingga 3 item secara paralel. Progress per-item ditampilkan secara real-time.

---

## Pengaturan

Buka menu **Pengaturan (5)** untuk mengubah konfigurasi:

| No | Setting | Default | Keterangan |
|---|---|---|---|
| 1 | Path Video | `~/Downloads/YTDL_Video` | Folder tujuan video |
| 2 | Path Audio | `~/Downloads/YTDL_Music` | Folder tujuan audio |
| 3 | Resolusi Video | `1080p Full HD` | Max / 1080p / 720p / 480p / 360p |
| 4 | Format Audio | `MP3` | mp3 / flac / wav / opus / m4a |
| 5 | Kualitas Audio | `192 kbps` | 64 / 96 / 128 / 160 / 192 / 256 / 320 / 0 |
| 6 | Aria2c | Ya | Aktifkan akselerasi multi-koneksi |
| 7 | Max Koneksi | `10` | Jumlah koneksi aria2c (1–32) |
| 8 | Thumbnail | Ya | Embed thumbnail ke file |
| 9 | Subtitel | Ya | Embed & unduh subtitel (video) |
| 10 | Embed Lirik | Ya | Cari dan tanam lirik ke audio |
| 11 | Simpan .lrc | Tidak | Simpan file lirik sidecar `.lrc` |

> **Resolusi Video** menggunakan submenu bernomor — tidak perlu mengetik manual.

Konfigurasi disimpan otomatis ke `~/.ytdl_ultimate/config.json`.

---

## Format yang Didukung

### Audio

| Format | Tipe | Keterangan |
|---|---|---|
| `mp3` | Lossy | Paling kompatibel, default |
| `flac` | Lossless | Kualitas tertinggi, file lebih besar |
| `wav` | Lossless PCM | Tanpa kompresi |
| `opus` | Lossy | Efisien, kualitas tinggi di bitrate rendah |
| `m4a` | Lossy (AAC) | Kompatibel Apple |

### Video

Semua video diunduh dan digabung ke **MP4**. Resolusi dipilih dari pengaturan:

| Pilihan | Keterangan |
|---|---|
| Max | Resolusi tertinggi yang tersedia |
| 1080p | Full HD (default) |
| 720p | HD |
| 480p | SD |
| 360p | Low |

---

## Sistem Lirik

Lirik diambil otomatis dari **[lrclib.net](https://lrclib.net)** setelah setiap download audio berhasil (jika `embed_lyrics` aktif).

**Alur kerja:**
1. Judul video dibersihkan dari noise (kata seperti "Official Video", "ft.", "[MV]", dll.)
2. Pencarian dilakukan dengan beberapa variasi query (judul + artis, judul saja, dst.)
3. Hasil diprioritaskan: lirik tersinkronisasi (LRC) lebih diutamakan dari teks biasa
4. Untuk MP3: lirik tersinkronisasi ditanam sebagai tag **SYLT**; lirik teks biasa sebagai **USLT**
5. Untuk FLAC: disimpan di tag `LYRICS`
6. Untuk format lain (opus, wav, m4a): disimpan sebagai file `.lrc` sidecar
7. Semua hasil di-cache ke `~/.ytdl_ultimate/lyrics_cache.json` untuk menghindari request berulang

---

## Struktur File Aplikasi

Semua data aplikasi disimpan di `~/.ytdl_ultimate/`:

```
~/.ytdl_ultimate/
├── config.json        ← konfigurasi pengguna
├── history.json       ← riwayat download (maks. 1000 entri)
├── lyrics_cache.json  ← cache lirik (key: MD5 dari judul+artis)
├── cookies.txt        ← cookie YouTube (opsional, isi manual)
└── ytdl.log           ← log debug lengkap
```

### Menggunakan Cookie (untuk konten terbatas usia / akun)

Letakkan file cookie Netscape-format di `~/.ytdl_ultimate/cookies.txt`. Cookie akan otomatis digunakan oleh semua request yt-dlp. Cara export cookie dari browser menggunakan ekstensi [Get cookies.txt LOCALLY](https://chrome.google.com/webstore/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc).

---

## Struktur Kode

```
ytdl/
├── __init__.py      Dokumentasi package
├── constants.py     Logging, dependency check, semua konstanta & DEFAULT_CONFIG
├── utils.py         sanitize_filename, validate_url, exponential_backoff
├── ui.py            C (warna), G (glyph), Layout, UI, Spinner
├── lyrics.py        LyricsManager — fetch, embed, simpan .lrc
├── config.py        ConfigManager — load, validasi, simpan
├── history.py       HistoryManager — riwayat thread-safe
├── engine.py        Engine — download, download_playlist, progress
├── settings.py      SettingsMenu
└── main.py          App (main loop) + entry point
```

---

## Troubleshooting

**`yt-dlp` tidak ditemukan**
```bash
pip install yt-dlp
# atau update jika sudah terinstal
pip install -U yt-dlp
```

**`ffmpeg` tidak ditemukan / konversi gagal**
Pastikan `ffmpeg` terinstal dan bisa diakses dari PATH. Tanpa ffmpeg, konversi audio dan penggabungan video tidak bisa dilakukan.

**Lirik tidak ditemukan**
Lrclib.net mungkin tidak memiliki lirik untuk lagu tersebut, atau judul video terlalu berbeda dari judul lagu sebenarnya. Aktifkan `Simpan .lrc` di pengaturan untuk menyimpan lirik ke file terpisah sebagai fallback.

**Download gagal terus**
Periksa log di menu **Lihat Log Debug (7)** atau buka langsung `~/.ytdl_ultimate/ytdl.log`. Error umum biasanya terkait rate limiting YouTube — coba tambahkan cookie.

**Di Termux, folder `/sdcard` tidak bisa diakses**
Jalankan `termux-setup-storage` secara manual dan berikan izin penyimpanan, lalu restart aplikasi.

---

## Lisensi

Proyek ini bebas digunakan dan dimodifikasi untuk keperluan pribadi.
