"""
COD Highlight Cutter v3.0 - Configuration
"""
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
ASSETS_DIR = os.path.join(BASE_DIR, "assets")

# Video Processing
VIDEO_FPS = 60
VIDEO_RESOLUTION = (1920, 1080)
CLIP_PADDING_BEFORE = 2.0   # seconds before kill
CLIP_PADDING_AFTER = 3.0    # seconds after kill
MIN_CLIP_DURATION = 3.0     # minimum clip length
MAX_CLIP_DURATION = 20.0    # maximum clip length

# Kill/Death Detection
KILL_CONFIDENCE_THRESHOLD = 0.75
DEATH_CONFIDENCE_THRESHOLD = 0.75
DETECTION_COOLDOWN = 3.0    # seconds between detections
OCR_LANG = "eng"

# Audio
TARGET_AUDIO_DB = -14.0     # LUFS target
NORMALIZE_AUDIO = True
FADE_IN_DURATION = 0.3
FADE_OUT_DURATION = 0.5

# Effects
KILL_EFFECTS = ["slowmo", "zoom", "shake", "flash"]
DEATH_EFFECTS = ["blur", "desaturate", "slowmo"]
MULTIKILL_EFFECTS = ["cinematic_bars", "intense_zoom", "color_boost"]

# Intro/Outro
INTRO_DURATION = 5.0
OUTRO_DURATION = 5.0
TRANSITION_DURATION = 1.0

# TikTok Export
TIKTOK_RESOLUTION = (1080, 1920)
TIKTOK_FPS = 60

# Export
VIDEO_CODEC = "libx264"
AUDIO_CODEC = "aac"
VIDEO_BITRATE = "20M"
AUDIO_BITRATE = "320k"
PRESET = "slow"
CRF = 18
