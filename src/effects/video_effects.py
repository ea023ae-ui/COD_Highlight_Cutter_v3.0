"""
COD Highlight Cutter v3.0 - Video Effects Engine
Handles: slow motion, zoom, shake, flash, blur, color grading, cinematic bars
"""
import cv2
import numpy as np
from moviepy.editor import *
from moviepy.video.fx.all import *
import os

class EffectsEngine:
    """
    Complete effects pipeline:
    1. Slow motion (speed ramping)
    2. Zoom (center/target tracking)
    3. Camera shake
    4. Screen flash
    5. Motion blur
    6. Color grading (desaturate, boost, tint)
    7. Cinematic bars
    8. Text overlays (kill counters, multikill badges)
    """

    def __init__(self):
        self.effects_registry = {
            "slowmo": self.apply_slow_motion,
            "zoom": self.apply_zoom,
            "shake": self.apply_shake,
            "flash": self.apply_flash,
            "blur": self.apply_blur,
            "desaturate": self.apply_desaturate,
            "color_boost": self.apply_color_boost,
            "cinematic_bars": self.apply_cinematic_bars,
            "intense_zoom": self.apply_intense_zoom,
            "text_overlay": self.apply_text_overlay,
            "kill_badge": self.apply_kill_badge,
            "multikill_badge": self.apply_multikill_badge,
            "transition_fade": self.apply_fade_transition,
            "transition_zoom": self.apply_zoom_transition,
        }

    def apply_effects_to_clip(self, clip: VideoFileClip, effects: list, 
                              event_type: str = "kill") -> VideoFileClip:
        """
        Apply a chain of effects to a video clip.
        effects: list of dicts with keys: name, params, start, duration
        """
        for effect in effects:
            effect_name = effect.get("name")
            params = effect.get("params", {})
            start = effect.get("start", 0)
            duration = effect.get("duration", clip.duration)

            if effect_name in self.effects_registry:
                clip = self.effects_registry[effect_name](clip, start, duration, **params)

        return clip

    def get_kill_effects(self, event_type: str = "kill", multikill_count: int = 1) -> list:
        """Get default effects configuration for different event types."""

        if event_type == "kill":
            return [
                {"name": "zoom", "start": 0, "duration": 0.5, "params": {"zoom_factor": 1.3, "ease": "ease_out"}},
                {"name": "flash", "start": 0, "duration": 0.3, "params": {"color": (255, 255, 255), "intensity": 0.3}},
                {"name": "shake", "start": 0, "duration": 0.4, "params": {"intensity": 3, "frequency": 15}},
                {"name": "slowmo", "start": 0, "duration": 1.0, "params": {"speed": 0.5, "ramp_duration": 0.3}},
                {"name": "kill_badge", "start": 0.2, "duration": 1.5, "params": {"badge_type": "kill"}},
            ]

        elif event_type == "death":
            return [
                {"name": "blur", "start": 0, "duration": 1.0, "params": {"blur_amount": 8}},
                {"name": "desaturate", "start": 0, "duration": 1.0, "params": {"factor": 0.7}},
                {"name": "slowmo", "start": 0, "duration": 1.5, "params": {"speed": 0.3, "ramp_duration": 0.5}},
                {"name": "text_overlay", "start": 0.5, "duration": 1.0, "params": {"text": "ELIMINATED", "color": "red"}},
            ]

        elif event_type.startswith("multikill"):
            count = multikill_count
            return [
                {"name": "intense_zoom", "start": 0, "duration": 0.8, "params": {"zoom_factor": 1.5}},
                {"name": "color_boost", "start": 0, "duration": 1.0, "params": {"saturation": 1.5, "contrast": 1.2}},
                {"name": "cinematic_bars", "start": 0, "duration": 2.0, "params": {"bar_height": 80}},
                {"name": "shake", "start": 0, "duration": 0.6, "params": {"intensity": 5, "frequency": 20}},
                {"name": "multikill_badge", "start": 0.1, "duration": 2.0, "params": {"count": count}},
                {"name": "slowmo", "start": 0, "duration": 1.5, "params": {"speed": 0.4, "ramp_duration": 0.2}},
            ]

        elif event_type == "headshot":
            return [
                {"name": "zoom", "start": 0, "duration": 0.3, "params": {"zoom_factor": 1.4, "ease": "ease_out"}},
                {"name": "flash", "start": 0, "duration": 0.2, "params": {"color": (255, 50, 50), "intensity": 0.5}},
                {"name": "text_overlay", "start": 0.1, "duration": 1.0, "params": {"text": "HEADSHOT", "color": "yellow"}},
            ]

        return []

    # ============ INDIVIDUAL EFFECTS ============

    def apply_slow_motion(self, clip: VideoFileClip, start: float, duration: float,
                          speed: float = 0.5, ramp_duration: float = 0.3) -> VideoFileClip:
        """Apply smooth slow motion with speed ramping."""
        def speed_func(t):
            """Speed curve: normal -> slow -> normal"""
            if t < start:
                return 1.0
            elif t < start + ramp_duration:
                # Ramp down
                progress = (t - start) / ramp_duration
                return 1.0 - (1.0 - speed) * progress
            elif t < start + duration - ramp_duration:
                return speed
            elif t < start + duration:
                # Ramp up
                progress = (t - (start + duration - ramp_duration)) / ramp_duration
                return speed + (1.0 - speed) * progress
            else:
                return 1.0

        return clip.fl_time(lambda t: self._integrate_speed(speed_func, t, start))

    def _integrate_speed(self, speed_func, t, start):
        """Helper to integrate speed function for time remapping."""
        # Simplified: use numpy for integration
        dt = 0.01
        times = np.arange(0, t + dt, dt)
        speeds = [speed_func(ti) for ti in times]
        return np.trapz(speeds, times)

    def apply_zoom(self, clip: VideoFileClip, start: float, duration: float,
                   zoom_factor: float = 1.3, ease: str = "ease_out") -> VideoFileClip:
        """Apply smooth zoom effect."""
        def zoom_func(t):
            if t < start:
                return 1.0
            elif t < start + duration:
                progress = (t - start) / duration
                if ease == "ease_out":
                    progress = 1 - (1 - progress) ** 2
                elif ease == "ease_in":
                    progress = progress ** 2
                return 1.0 + (zoom_factor - 1.0) * progress
            else:
                return zoom_factor

        def effect(get_frame, t):
            frame = get_frame(t)
            z = zoom_func(t)
            h, w = frame.shape[:2]

            # Calculate crop region
            new_h, new_w = int(h / z), int(w / z)
            y1 = (h - new_h) // 2
            x1 = (w - new_w) // 2

            cropped = frame[y1:y1+new_h, x1:x1+new_w]
            return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LANCZOS4)

        return clip.fl(effect)

    def apply_intense_zoom(self, clip: VideoFileClip, start: float, duration: float,
                           zoom_factor: float = 1.5) -> VideoFileClip:
        """More aggressive zoom for multikills."""
        return self.apply_zoom(clip, start, duration, zoom_factor, "ease_in_out")

    def apply_shake(self, clip: VideoFileClip, start: float, duration: float,
                    intensity: float = 3, frequency: float = 15) -> VideoFileClip:
        """Apply camera shake effect."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            # Generate shake offset
            progress = (t - start) / duration
            decay = 1.0 - progress  # Decay over time

            dx = int(intensity * decay * np.sin(2 * np.pi * frequency * progress))
            dy = int(intensity * decay * np.cos(2 * np.pi * frequency * progress * 1.3))

            M = np.float32([[1, 0, dx], [0, 1, dy]])
            return cv2.warpAffine(frame, M, (frame.shape[1], frame.shape[0]))

        return clip.fl(effect)

    def apply_flash(self, clip: VideoFileClip, start: float, duration: float,
                    color: tuple = (255, 255, 255), intensity: float = 0.3) -> VideoFileClip:
        """Apply screen flash effect."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            progress = (t - start) / duration
            # Flash curve: quick rise, slow fall
            flash_strength = intensity * np.exp(-5 * progress)

            flash_frame = np.full_like(frame, color, dtype=np.uint8)
            return cv2.addWeighted(frame, 1.0, flash_frame, flash_strength, 0)

        return clip.fl(effect)

    def apply_blur(self, clip: VideoFileClip, start: float, duration: float,
                   blur_amount: int = 8) -> VideoFileClip:
        """Apply Gaussian blur."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            progress = (t - start) / duration
            current_blur = int(blur_amount * (1 - progress * 0.5))
            current_blur = max(1, current_blur | 1)  # Ensure odd

            return cv2.GaussianBlur(frame, (current_blur, current_blur), 0)

        return clip.fl(effect)

    def apply_desaturate(self, clip: VideoFileClip, start: float, duration: float,
                         factor: float = 0.7) -> VideoFileClip:
        """Desaturate frame (death effect)."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            progress = (t - start) / duration
            current_factor = factor * (1 - progress * 0.3)

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray_3ch = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)

            return cv2.addWeighted(frame, 1 - current_factor, gray_3ch, current_factor, 0)

        return clip.fl(effect)

    def apply_color_boost(self, clip: VideoFileClip, start: float, duration: float,
                          saturation: float = 1.5, contrast: float = 1.2) -> VideoFileClip:
        """Boost colors for multikill excitement."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            # Convert to HSV, boost saturation
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV).astype(np.float32)
            hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
            hsv = hsv.astype(np.uint8)
            result = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)

            # Apply contrast
            result = cv2.convertScaleAbs(result, alpha=contrast, beta=0)

            return result

        return clip.fl(effect)

    def apply_cinematic_bars(self, clip: VideoFileClip, start: float, duration: float,
                             bar_height: int = 80) -> VideoFileClip:
        """Add cinematic black bars."""
        def effect(get_frame, t):
            frame = get_frame(t)

            if t < start or t > start + duration:
                return frame

            h, w = frame.shape[:2]
            frame[:bar_height, :] = 0  # Top bar
            frame[-bar_height:, :] = 0  # Bottom bar

            return frame

        return clip.fl(effect)

    def apply_text_overlay(self, clip: VideoFileClip, start: float, duration: float,
                           text: str = "TEXT", color: str = "white", 
                           font_size: int = 60, position: str = "center") -> VideoFileClip:
        """Add text overlay to clip."""
        txt_clip = (TextClip(text, fontsize=font_size, color=color, 
                             font="Arial-Bold", stroke_color="black", stroke_width=2)
                    .set_duration(duration)
                    .set_start(start)
                    .set_pos(position))

        # Animate text
        txt_clip = txt_clip.fx(vfx.fadein, 0.2).fx(vfx.fadeout, 0.3)

        return CompositeVideoClip([clip, txt_clip])

    def apply_kill_badge(self, clip: VideoFileClip, start: float, duration: float,
                         badge_type: str = "kill") -> VideoFileClip:
        """Add animated kill badge."""
        badge_text = "KILL" if badge_type == "kill" else badge_type.upper()
        colors = {"kill": "#00ff00", "headshot": "#ffff00"}
        color = colors.get(badge_type, "#00ff00")

        txt_clip = (TextClip(badge_text, fontsize=80, color=color,
                             font="Impact", stroke_color="black", stroke_width=3)
                    .set_duration(duration)
                    .set_start(start)
                    .set_pos(("center", "top")))

        # Scale animation
        txt_clip = txt_clip.resize(lambda t: 1 + 0.3 * np.sin(10 * t) if t < 0.5 else 1.0)
        txt_clip = txt_clip.fx(vfx.fadein, 0.1).fx(vfx.fadeout, 0.3)

        return CompositeVideoClip([clip, txt_clip])

    def apply_multikill_badge(self, clip: VideoFileClip, start: float, duration: float,
                              count: int = 2) -> VideoFileClip:
        """Add multikill badge with count."""
        badges = {2: "DOUBLE KILL", 3: "TRIPLE KILL", 4: "QUAD KILL", 5: "FURY KILL"}
        badge_text = badges.get(count, f"x{count} KILL")

        txt_clip = (TextClip(badge_text, fontsize=100, color="#ff3333",
                             font="Impact", stroke_color="white", stroke_width=4)
                    .set_duration(duration)
                    .set_start(start)
                    .set_pos("center"))

        # Pulse animation
        txt_clip = txt_clip.resize(lambda t: 1 + 0.2 * np.sin(8 * t))
        txt_clip = txt_clip.fx(vfx.fadein, 0.1).fx(vfx.fadeout, 0.5)

        return CompositeVideoClip([clip, txt_clip])

    def apply_fade_transition(self, clip1: VideoFileClip, clip2: VideoFileClip,
                              duration: float = 0.5) -> VideoFileClip:
        """Crossfade between two clips."""
        return concatenate_videoclips([clip1, clip2], method="compose")

    def apply_zoom_transition(self, clip1: VideoFileClip, clip2: VideoFileClip,
                              duration: float = 0.5) -> VideoFileClip:
        """Zoom transition between clips."""
        # Zoom out clip1, zoom in clip2
        clip1_zoomed = clip1.fx(vfx.resize, lambda t: 1 + 0.3 * t / clip1.duration)
        clip2_zoomed = clip2.fx(vfx.resize, lambda t: 1.3 - 0.3 * t / clip2.duration)

        return concatenate_videoclips([clip1_zoomed, clip2_zoomed], method="compose")

    def create_intro(self, duration: float = 5.0, text: str = "COD HIGHLIGHTS",
                     music_path: str = None, resolution: tuple = (1920, 1080)) -> VideoFileClip:
        """Create intro clip."""
        # Black background
        bg = ColorClip(size=resolution, color=(10, 10, 15), duration=duration)

        # Animated text
        txt = (TextClip(text, fontsize=100, color="white",
                        font="Impact", stroke_color="red", stroke_width=3)
               .set_duration(duration)
               .set_pos("center"))

        # Add glow effect by layering
        txt_glow = (TextClip(text, fontsize=105, color="red",
                             font="Impact")
                    .set_duration(duration)
                    .set_pos("center")
                    .set_opacity(0.3))

        intro = CompositeVideoClip([bg, txt_glow, txt])
        intro = intro.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 0.5)

        if music_path and os.path.exists(music_path):
            audio = AudioFileClip(music_path).subclip(0, duration)
            audio = audio.fx(afx.audio_fadein, 0.5).fx(afx.audio_fadeout, 0.5)
            intro = intro.set_audio(audio)

        return intro

    def create_outro(self, duration: float = 5.0, text: str = "THANKS FOR WATCHING",
                     subtext: str = "Like & Subscribe",
                     music_path: str = None, resolution: tuple = (1920, 1080)) -> VideoFileClip:
        """Create outro clip."""
        bg = ColorClip(size=resolution, color=(10, 10, 15), duration=duration)

        main_txt = (TextClip(text, fontsize=80, color="white",
                             font="Impact", stroke_color="blue", stroke_width=2)
                    .set_duration(duration)
                    .set_pos(("center", "center")))

        sub_txt = (TextClip(subtext, fontsize=40, color="#aaaaaa",
                            font="Arial")
                   .set_duration(duration)
                   .set_pos(("center", "center"))
                   .margin(top=120, opacity=0))

        outro = CompositeVideoClip([bg, main_txt, sub_txt])
        outro = outro.fx(vfx.fadein, 0.5).fx(vfx.fadeout, 1.0)

        if music_path and os.path.exists(music_path):
            audio = AudioFileClip(music_path).subclip(0, duration)
            audio = audio.fx(afx.audio_fadein, 0.5).fx(afx.audio_fadeout, 1.0)
            outro = outro.set_audio(audio)

        return outro
