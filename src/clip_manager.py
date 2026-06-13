"""
COD Highlight Cutter v3.0 - Clip Manager
Handles: trimming clips, joining clips, creating intro/outro, transitions
"""
import os
import cv2
import numpy as np
from moviepy.editor import *
from moviepy.video.fx.all import *
from typing import List, Tuple, Optional
import shutil

from .detectors.kill_detector import Event
from .effects.video_effects import EffectsEngine
from .audio.audio_processor import AudioProcessor

class ClipManager:
    """
    Complete clip management:
    1. Extract clips around kill/death events with smart padding
    2. Apply effects to each clip
    3. Add audio processing per clip
    4. Join clips with transitions
    5. Add intro/outro
    6. Export final video
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.effects_engine = EffectsEngine()
        self.audio_processor = AudioProcessor()

        # Default settings
        self.padding_before = self.config.get("padding_before", 2.0)
        self.padding_after = self.config.get("padding_after", 3.0)
        self.min_duration = self.config.get("min_duration", 3.0)
        self.max_duration = self.config.get("max_duration", 20.0)
        self.transition_duration = self.config.get("transition_duration", 0.5)
        self.resolution = self.config.get("resolution", (1920, 1080))
        self.fps = self.config.get("fps", 60)

    def create_highlight_video(self, video_path: str, events: List[Event],
                               output_path: str,
                               intro_config: dict = None,
                               outro_config: dict = None,
                               music_path: str = None,
                               add_kill_sounds: bool = True,
                               export_individual: bool = False) -> str:
        """
        Main pipeline: events -> clips -> effects -> audio -> join -> intro/outro -> export.
        """
        print(f"[ClipManager] Processing {len(events)} events from {video_path}")

        # Step 1: Extract clips
        clips = self.extract_clips(video_path, events)
        print(f"[ClipManager] Extracted {len(clips)} clips")

        if not clips:
            print("[ClipManager] No clips found!")
            return None

        # Step 2: Process each clip (effects + audio)
        processed_clips = []
        for i, (clip, event) in enumerate(zip(clips, events)):
            print(f"[ClipManager] Processing clip {i+1}/{len(clips)}: {event.event_type} @ {event.timestamp:.1f}s")

            # Apply effects
            effects = self.effects_engine.get_kill_effects(
                event.event_type,
                multikill_count=self._get_multikill_count(event.event_type)
            )
            clip = self.effects_engine.apply_effects_to_clip(clip, effects, event.event_type)

            # Process audio
            if clip.audio is not None:
                temp_audio = os.path.join(os.path.dirname(output_path), f"temp_audio_{i}.wav")
                clip.audio.write_audiofile(temp_audio, fps=48000, verbose=False, logger=None)

                processed_audio = self.audio_processor.process_clip_audio(
                    temp_audio, 0, clip.duration,
                    add_kill_sound=add_kill_sounds and event.event_type in ["kill", "multikill_x2", "multikill_x3"],
                    add_music=False
                )
                clip = clip.set_audio(AudioFileClip(processed_audio))

                # Cleanup temp
                os.remove(temp_audio)
                os.remove(processed_audio)

            processed_clips.append(clip)

            # Export individual if requested
            if export_individual:
                individual_path = output_path.replace(".mp4", f"_clip_{i+1:02d}.mp4")
                clip.write_videofile(individual_path, codec="libx264", audio_codec="aac",
                                     fps=self.fps, preset="fast", threads=4,
                                     verbose=False, logger=None)
                print(f"[ClipManager] Saved individual clip: {individual_path}")

        # Step 3: Join clips with transitions
        if len(processed_clips) > 1:
            final_clip = self.join_clips(processed_clips, transition_type="fade")
        else:
            final_clip = processed_clips[0]

        # Step 4: Add intro
        if intro_config:
            intro = self.effects_engine.create_intro(
                duration=intro_config.get("duration", 5.0),
                text=intro_config.get("text", "COD HIGHLIGHTS"),
                music_path=intro_config.get("music_path"),
                resolution=self.resolution
            )
            final_clip = concatenate_videoclips([intro, final_clip], method="compose")

        # Step 5: Add outro
        if outro_config:
            outro = self.effects_engine.create_outro(
                duration=outro_config.get("duration", 5.0),
                text=outro_config.get("text", "THANKS FOR WATCHING"),
                subtext=outro_config.get("subtext", "Like & Subscribe"),
                music_path=outro_config.get("music_path"),
                resolution=self.resolution
            )
            final_clip = concatenate_videoclips([final_clip, outro], method="compose")

        # Step 6: Add background music to full video
        if music_path and os.path.exists(music_path):
            # Extract full audio, mix music, reattach
            temp_full_audio = output_path.replace(".mp4", "_full_audio.wav")
            final_clip.audio.write_audiofile(temp_full_audio, fps=48000, verbose=False, logger=None)

            mixed_audio = self.audio_processor.add_background_music(
                temp_full_audio, music_path,
                music_volume_db=-22,
                ducking=True
            )
            final_clip = final_clip.set_audio(AudioFileClip(mixed_audio))
            os.remove(temp_full_audio)
            os.remove(mixed_audio)

        # Step 7: Export
        print(f"[ClipManager] Exporting final video to {output_path}")
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=self.fps,
            preset="slow",
            threads=8,
            bitrate="20M",
            audio_bitrate="320k",
            verbose=False,
            logger=None
        )

        # Cleanup
        for clip in processed_clips:
            clip.close()
        if intro_config:
            intro.close()
        if outro_config:
            outro.close()
        final_clip.close()

        print(f"[ClipManager] Done! Output: {output_path}")
        return output_path

    def extract_clips(self, video_path: str, events: List[Event]) -> List[VideoFileClip]:
        """
        Extract video clips around events with smart padding.
        Handles overlapping clips by merging them.
        """
        video = VideoFileClip(video_path)
        duration = video.duration

        # Calculate clip boundaries
        clips_data = []
        for event in events:
            start = max(0, event.timestamp - self.padding_before)
            end = min(duration, event.timestamp + self.padding_after)

            # Enforce min/max duration
            if end - start < self.min_duration:
                end = min(duration, start + self.min_duration)
            if end - start > self.max_duration:
                end = start + self.max_duration

            clips_data.append({
                "start": start,
                "end": end,
                "event": event,
                "priority": self._get_event_priority(event)
            })

        # Merge overlapping clips
        clips_data = self._merge_overlapping_clips(clips_data)

        # Extract clips
        clips = []
        for data in clips_data:
            clip = video.subclip(data["start"], data["end"])
            clips.append(clip)

        return clips

    def _merge_overlapping_clips(self, clips_data: List[dict]) -> List[dict]:
        """Merge clips that overlap, keeping highest priority event info."""
        if not clips_data:
            return []

        # Sort by start time
        clips_data.sort(key=lambda x: x["start"])

        merged = [clips_data[0]]

        for current in clips_data[1:]:
            last = merged[-1]

            # Check overlap (with small gap tolerance)
            if current["start"] <= last["end"] + 0.5:
                # Merge: extend end, keep higher priority event
                last["end"] = max(last["end"], current["end"])
                if current["priority"] > last["priority"]:
                    last["event"] = current["event"]
                    last["priority"] = current["priority"]
            else:
                merged.append(current)

        return merged

    def _get_event_priority(self, event: Event) -> int:
        """Priority for merging: higher = more important."""
        priorities = {
            "multikill_x5": 10, "multikill_x4": 9, "multikill_x3": 8,
            "multikill_x2": 7, "headshot": 6, "kill": 5,
            "death": 3, "possible_kill": 2
        }
        return priorities.get(event.event_type, 1)

    def _get_multikill_count(self, event_type: str) -> int:
        """Extract multikill count from event type."""
        if event_type.startswith("multikill_x"):
            try:
                return int(event_type.split("x")[1])
            except:
                return 2
        return 1

    def join_clips(self, clips: List[VideoFileClip], 
                   transition_type: str = "fade") -> VideoFileClip:
        """
        Join multiple clips with transitions.
        transition_type: "fade", "zoom", "cut", "slide"
        """
        if len(clips) == 1:
            return clips[0]

        if transition_type == "cut":
            return concatenate_videoclips(clips, method="compose")

        # Apply transitions between clips
        final_clips = [clips[0]]

        for i in range(1, len(clips)):
            prev_clip = final_clips[-1]
            curr_clip = clips[i]

            if transition_type == "fade":
                # Crossfade
                prev_clip = prev_clip.fx(vfx.fadeout, self.transition_duration)
                curr_clip = curr_clip.fx(vfx.fadein, self.transition_duration)
                final_clips[-1] = prev_clip
                final_clips.append(curr_clip)

            elif transition_type == "zoom":
                # Zoom transition
                joined = self.effects_engine.apply_zoom_transition(
                    prev_clip, curr_clip, self.transition_duration
                )
                final_clips[-1] = joined

            elif transition_type == "slide":
                # Slide transition
                w = prev_clip.w
                def slide(t):
                    if t < self.transition_duration:
                        return (-w * t / self.transition_duration, "center")
                    else:
                        return ("center", "center")

                curr_clip = curr_clip.set_position(slide)
                final_clips[-1] = CompositeVideoClip([prev_clip, curr_clip.set_start(prev_clip.duration - self.transition_duration)])

        return concatenate_videoclips(final_clips, method="compose")

    def create_tiktok_export(self, video_path: str, events: List[Event],
                            output_path: str, 
                            resolution: Tuple[int, int] = (1080, 1920)) -> str:
        """Create TikTok vertical format export."""
        print(f"[ClipManager] Creating TikTok export: {resolution}")

        clips = self.extract_clips(video_path, events)

        tiktok_clips = []
        for clip, event in zip(clips, events):
            # Resize to TikTok format (center crop)
            w, h = resolution
            target_ratio = w / h  # 9:16

            current_ratio = clip.w / clip.h  # 16:9 = 1.777

            if current_ratio > target_ratio:
                # Crop sides
                new_w = int(clip.h * target_ratio)
                x1 = (clip.w - new_w) // 2
                clip = clip.crop(x1=x1, y1=0, x2=x1+new_w, y2=clip.h)
            else:
                # Crop top/bottom
                new_h = int(clip.w / target_ratio)
                y1 = (clip.h - new_h) // 2
                clip = clip.crop(x1=0, y1=y1, x2=clip.w, y2=y1+new_h)

            # Resize
            clip = clip.resize(resolution)

            # Add TikTok-style text
            effects = self.effects_engine.get_kill_effects(event.event_type)
            clip = self.effects_engine.apply_effects_to_clip(clip, effects, event.event_type)

            tiktok_clips.append(clip)

        # Join
        if len(tiktok_clips) > 1:
            final = self.join_clips(tiktok_clips, "fade")
        else:
            final = tiktok_clips[0]

        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            fps=60,
            preset="fast",
            threads=4,
            verbose=False,
            logger=None
        )

        print(f"[ClipManager] TikTok export done: {output_path}")
        return output_path
