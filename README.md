# COD Highlight Cutter v3.0

## What's New in v3.0

### Fixed Issues from v2.1
1. **Video Sound** - Full audio pipeline: extraction, normalization (LUFS), fades, sound effects mixing
2. **Effects & Sound** - 12+ effects: slowmo, zoom, shake, flash, blur, desaturate, color boost, cinematic bars, text overlays, kill/multikill badges
3. **Smart Kill/Death Detection** - Multi-modal fusion: OCR + visual HUD analysis + audio spike detection + hit marker recognition
4. **Join Many Clips** - Smart clip merging (overlaps), crossfade/zoom/slide transitions, TikTok export
5. **Intro & Outro** - Animated intro/outro with custom text, music, fade animations

## Quick Start

### Method 1: Drag & Drop
1. Drag your COD gameplay video onto `Start.bat`
2. Wait for processing
3. Find output in `output/` folder

### Method 2: Command Line
```bash
# Basic usage
python main.py "gameplay.mp4"

# With custom intro/outro and music
python main.py "gameplay.mp4" --intro "MY CLIPS" --outro "GG" --music "music.mp3"

# TikTok export + individual clips
python main.py "gameplay.mp4" --tiktok --individual

# Detection only (review events before processing)
python main.py "gameplay.mp4" --detect-only --events-json events.json

# Adjust detection sensitivity
python main.py "gameplay.mp4" --confidence 0.8 --padding-before 3 --padding-after 4
```

## Project Structure
```
COD_Highlight_Cutter_v3.0/
├── Start.bat              # One-click launcher + auto-installer
├── main.py                # Main controller
├── requirements.txt       # Dependencies
├── config/
│   └── settings.py        # All configuration
├── src/
│   ├── detectors/
│   │   └── kill_detector.py      # Smart kill/death detection (OCR + visual + audio)
│   ├── effects/
│   │   └── video_effects.py      # Effects engine (12+ effects)
│   ├── audio/
│   │   └── audio_processor.py    # Audio pipeline (extract, normalize, mix)
│   ├── utils/
│   │   └── logger.py             # Logging
│   └── clip_manager.py           # Clip extraction, joining, intro/outro
├── assets/
│   ├── sound_effects/     # Place kill confirmation sounds here
│   ├── music/             # Place background music here
│   ├── intro_templates/   # Custom intro assets
│   └── outro_templates/   # Custom outro assets
├── output/                # Final videos
└── temp/                  # Temporary files
```

## Detection Methods

### 1. OCR Text Detection
- Scans kill feed (top-right), center popups, death cam, scoreboard
- Recognizes: "eliminated", "killed", "takedown", "you died", "double kill", etc.
- Confidence scoring based on text clarity

### 2. Visual HUD Analysis
- Hit marker detection (red/white crosshair)
- Screen flash detection (death/respawn)
- Kill cam border detection (darkened edges)

### 3. Audio Spike Detection
- Gunshot classification (high/mid frequency)
- Explosion detection (low frequency)
- Synced with video frames for confirmation

### 4. Multi-Modal Fusion
- Kill = OCR + hit marker + audio spike
- Death = OCR + screen flash + kill cam
- Multikill = consecutive kills within 4 seconds

## Effects Catalog

| Effect | Description | Trigger |
|--------|-------------|---------|
| Slow Motion | Speed ramping (0.3x - 0.5x) | Kill, Death, Multikill |
| Zoom | Smooth center zoom (1.3x - 1.5x) | Kill, Headshot |
| Camera Shake | Intensity decay shake | Kill, Multikill |
| Screen Flash | White/red flash overlay | Kill, Headshot |
| Blur | Gaussian blur | Death |
| Desaturate | Color drain to grayscale | Death |
| Color Boost | Saturation + contrast boost | Multikill |
| Cinematic Bars | Black bars top/bottom | Multikill |
| Kill Badge | "KILL" text overlay | Kill |
| Multikill Badge | "DOUBLE KILL" etc. | Multikill |
| Headshot Badge | "HEADSHOT" text | Headshot |

## Configuration

Edit `config/settings.py` to customize:
- Video resolution, FPS, bitrate
- Detection confidence thresholds
- Clip padding (before/after events)
- Effect parameters
- Audio normalization target

## Requirements

- Python 3.9+
- Tesseract OCR (for text detection)
- 8GB+ RAM recommended
- NVIDIA GPU optional (for faster processing)

## License

Personal use only.
