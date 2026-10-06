# StandUpTimer

A lightweight, always-on-top stand-up timer for Windows. Built with Python + PyQt6, packaged as a single `.exe` via PyInstaller.

![StandUpTimer screenshot](assets/screenshot.png)

---

## Features

- **Circular visual timer** — big, coloured ring that shrinks/grows
- **Multiple team profiles** — each with its own colleague-image folder, auto-start time, statistics
- **Auto-start** — launch at a set time every weekday (e.g. 09:00)
- **Count-down / count-up modes**
- **Per-person cumulative statistics** — persisted per profile
- **Drag-to-move**, right-click for context menu
- **Frameless, translucent, stays on top** — zero chrome
- **Shuffle / no-shuffle restart**, ±1/5 min time adjust
- **Name overlays** — optional first-name display with size/position sliders
- **Settings stored in registry** (`HKEY_CURRENT_USER\Software\MyCompany\StandupTimer`)

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/aundal/StandUpTimer.git
cd StandUpTimer

# 2. Create a folder with colleague photos (PNG/JPG, one per person)
mkdir colleagues
# drop files like alice.png, bob.jpg, ...

# 3. Run (dev)
pip install -r requirements.txt   # PyQt6
python standup_timer.13.py
```

Right-click the timer → **Settings** → pick your `colleagues` folder, set total time, enable auto-start, etc.

---

## Download

| Platform | Asset | SHA256 |
|---|---|---|
| Windows x64 | [StandUpTimer.exe](https://github.com/aundal/StandUpTimer/releases/download/v1.0.0/StandUpTimer.exe) | `9eb67814fc98e1fd2e5e083860aa16a350abadb469b828edef8cfb56243566d7` |

> The exe is **not code-signed**. Windows SmartScreen will warn — click *More info → Run anyway*.

---

## Build from source

```bash
pip install pyinstaller pyqt6
pyinstaller StandUpTimer.spec --clean
# → dist/StandUpTimer.exe  (≈ 21 MB, onefile, UPX-compressed)
```

`StandUpTimer.spec` excludes unnecessary Qt plugins / binaries to keep size down.

---

## Project structure

```
StandUpTimer/
├── standup_timer.13.py     # Single-file application (1629 lines)
├── StandUpTimer.spec       # PyInstaller spec
├── test_standup_timer.py   # 40+ unit tests (pure logic, no GUI)
├── ikon.ico / ikon.png     # App icon
├── colleagues/             # (user-created) put photos here
├── assets/                 # screenshots for README
├── requirements.txt        # PyQt6
├── LICENSE                 # MIT
└── .gitignore              # build/, dist/, __pycache__/, *.pyc
```

---

## Keyboard / mouse

| Action | Effect |
|---|---|
| **Drag** anywhere | Move window |
| **Right-click** | Context menu (Settings, Statistics, Profiles, Mode, Restart, Time, Exit) |
| **Click a face** | Toggle that person "removed" (skipped this round) |
| **Esc** | Close app (via context menu → Exit) |

---

## Configuration (persisted)

| Key | Default | Meaning |
|---|---|---|
| `time_limit` | 600 | Total seconds per stand-up |
| `ui_scale` | 1.0 | 0.5 – 3.0 |
| `image_dir` | `./colleagues` | Folder with colleague images |
| `auto_start_enabled` | false | Auto-start at `auto_start_time` |
| `auto_start_time` | "09:00" | HH:mm 24 h |
| `count_mode` | "countdown" | "countdown" or "countup" |
| `show_first_name_overlay` | false | Show first name on non-speakers |
| `name_overlay_size_percent` | 10 | 8 – 60 % |
| `name_overlay_position_percent` | 80 | 0 – 100 % from top |
| `profiles` | […] | Array of profile objects (see Settings dialog) |
| `person_totals_by_profile` | `{}` | Cumulative seconds per person per profile |

---

## Tests

```bash
python -m pytest test_standup_timer.py -v
# 41 tests, all logic helpers — no GUI required
```

---

## License

MIT — see [LICENSE](LICENSE).

---

## Author

Daniel Aundal · https://github.com/aundal