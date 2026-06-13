#!/usr/bin/env python3
"""
COD Highlight Cutter v3.0 - Main Controller

Usage:
    python main.py <video_path> [options]

    Options:
        --output PATH           Output file path
        --intro TEXT            Intro text (default: "COD HIGHLIGHTS")
        --outro TEXT            Outro text (default: "THANKS FOR WATCHING")
        --music PATH            Background music file
        --tiktok               Also export TikTok version
        --individual           Export individual clips
        --padding-before SEC   Seconds before event (default: 2.0)
        --padding-after SEC    Seconds after event (default: 3.0)
        --no-effects           Disable effects
        --no-audio-process     Disable audio processing
        --detect-only          Only run detection, don't create video
        --events-json PATH     Save/load detection events JSON
"""

import sys
import os
import argparse
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.detectors.kill_detector import SmartKillDeathDetector, Event
from src.effects.video_effects import EffectsEngine
from src.audio.audio_processor import AudioProcessor
from src.clip_manager import ClipManager
from src.utils.logger import get_logger
from config import settings

logger = get_logger("COD_Highlight_Cutter")


def parse_args():
    parser = argparse.ArgumentParser(description="COD Highlight Cutter v3.0")
    parser.add_argument("video", help="Input video file path")
    parser.add_argument("--output", "-o", default=None, help="Output file path")
    parser.add_argument("--intro", default="COD HIGHLIGHTS", help="Intro text")
    parser.add_argument("--outro", default="THANKS FOR WATCHING", help="Outro text")
    parser.add_argument("--subtext", default="Like & Subscribe", help="Outro subtext")
    parser.add_argument("--music", default=None, help="Background music path")
    parser.add_argument("--intro-music", default=None, help="Intro music path")
    parser.add_argument("--outro-music", default=None, help="Outro music path")
    parser.add_argument("--tiktok", action="store_true", help="Export TikTok version")
    parser.add_argument("--individual", action="store_true", help="Export individual clips")
    parser.add_argument("--padding-before", type=float, default=2.0, help="Padding before event")
    parser.add_argument("--padding-after", type=float, default=3.0, help="Padding after event")
    parser.add_argument("--no-effects", action="store_true", help="Disable effects")
    parser.add_argument("--no-audio-process", action="store_true", help="Disable audio processing")
    parser.add_argument("--detect-only", action="store_true", help="Only detect events")
    parser.add_argument("--events-json", default=None, help="Save/load events JSON")
    parser.add_argument("--confidence", type=float, default=0.6, help="Minimum detection confidence")
    parser.add_argument("--max-clips", type=int, default=50, help="Maximum clips to include")

    return parser.parse_args()


def main():
    args = parse_args()

    video_path = os.path.abspath(args.video)
    if not os.path.exists(video_path):
        logger.error(f"Video not found: {video_path}")
        sys.exit(1)

    # Setup output
    if args.output:
        output_path = os.path.abspath(args.output)
    else:
        base = os.path.splitext(video_path)[0]
        output_path = f"{base}_highlights_v3.mp4"

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    logger.info("=" * 60)
    logger.info("COD Highlight Cutter v3.0")
    logger.info("=" * 60)
    logger.info(f"Input:  {video_path}")
    logger.info(f"Output: {output_path}")

    # Step 1: Detect events
    logger.info("\n[Step 1/5] Detecting kills, deaths, and medals...")

    detector = SmartKillDeathDetector()

    # Check for cached events
    events = None
    if args.events_json and os.path.exists(args.events_json):
        logger.info(f"Loading cached events from {args.events_json}")
        with open(args.events_json, "r") as f:
            data = json.load(f)
            events = [Event(e["timestamp"], e["event_type"], e["confidence"], e.get("frame_data")) for e in data]

    if events is None:
        # Extract audio for sync detection
        audio_path = None
        if not args.no_audio_process:
            try:
                audio_processor = AudioProcessor()
                temp_dir = os.path.join(os.path.dirname(__file__), "temp")
                os.makedirs(temp_dir, exist_ok=True)
                audio_path = os.path.join(temp_dir, "temp_audio.wav")
                audio_processor.extract_audio(video_path, audio_path)
            except Exception as e:
                logger.warning(f"Audio extraction failed: {e}")

        events = detector.detect_from_video(video_path, audio_path)

        # Save events
        if args.events_json:
            detector.export_events_json(events, args.events_json)

    # Filter by confidence
    events = [e for e in events if e.confidence >= args.confidence]

    # Limit clips
    if len(events) > args.max_clips:
        logger.info(f"Limiting to top {args.max_clips} events by confidence")
        events.sort(key=lambda e: e.confidence, reverse=True)
        events = events[:args.max_clips]
        events.sort(key=lambda e: e.timestamp)

    logger.info(f"Found {len(events)} events after filtering")

    if args.detect_only:
        logger.info("Detect-only mode. Exiting.")
        return

    if not events:
        logger.warning("No events detected! Check your video or adjust confidence threshold.")
        return

    # Step 2: Create clips with effects
    logger.info("\n[Step 2/5] Creating highlight clips with effects...")

    config = {
        "padding_before": args.padding_before,
        "padding_after": args.padding_after,
        "resolution": settings.VIDEO_RESOLUTION,
        "fps": settings.VIDEO_FPS
    }

    clip_manager = ClipManager(config)

    # Prepare intro/outro configs
    intro_config = None
    if args.intro:
        intro_config = {
            "duration": settings.INTRO_DURATION,
            "text": args.intro,
            "music_path": args.intro_music
        }

    outro_config = None
    if args.outro:
        outro_config = {
            "duration": settings.OUTRO_DURATION,
            "text": args.outro,
            "subtext": args.subtext,
            "music_path": args.outro_music
        }

    # Step 3-7: Full pipeline
    logger.info("\n[Step 3/5] Processing clips and applying effects...")
    logger.info("[Step 4/5] Processing audio...")
    logger.info("[Step 5/5] Joining clips and exporting...")

    try:
        result = clip_manager.create_highlight_video(
            video_path=video_path,
            events=events,
            output_path=output_path,
            intro_config=intro_config,
            outro_config=outro_config,
            music_path=args.music,
            add_kill_sounds=not args.no_audio_process,
            export_individual=args.individual
        )

        if result:
            logger.info(f"\n✅ SUCCESS! Highlight video saved to:")
            logger.info(f"   {result}")

            # File size
            size_mb = os.path.getsize(result) / (1024 * 1024)
            logger.info(f"   File size: {size_mb:.1f} MB")

        # TikTok export
        if args.tiktok:
            tiktok_path = output_path.replace(".mp4", "_tiktok.mp4")
            logger.info(f"\n[TikTok] Creating vertical export...")
            clip_manager.create_tiktok_export(video_path, events, tiktok_path)
            logger.info(f"✅ TikTok export: {tiktok_path}")

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

    logger.info("\n" + "=" * 60)
    logger.info("All done! Enjoy your highlights!")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
