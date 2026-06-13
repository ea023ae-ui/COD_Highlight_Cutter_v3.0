"""
COD Highlight Cutter v3.0 - Audio Processor
Handles: extraction, normalization, sound effects mixing, fade in/out
"""
import numpy as np
import librosa
import soundfile as sf
from pydub import AudioSegment
from pydub.effects import normalize
import os
import subprocess

class AudioProcessor:
    """
    Complete audio pipeline:
    1. Extract audio from video
    2. Normalize to target LUFS
    3. Apply fades
    4. Mix sound effects
    5. Background music integration
    """

    def __init__(self, target_db=-14.0, fade_in=0.3, fade_out=0.5):
        self.target_db = target_db
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.sample_rate = 48000

    def extract_audio(self, video_path: str, output_path: str = None) -> str:
        """Extract audio from video using ffmpeg."""
        if output_path is None:
            output_path = video_path.replace(".mp4", "_audio.wav").replace(".avi", "_audio.wav")

        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vn", "-acodec", "pcm_s16le",
            "-ar", str(self.sample_rate),
            "-ac", "2",
            output_path
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"[Audio] ffmpeg error: {result.stderr}")
            raise RuntimeError("Failed to extract audio")

        print(f"[Audio] Extracted to {output_path}")
        return output_path

    def normalize_audio(self, audio_path: str, output_path: str = None) -> str:
        """Normalize audio to target LUFS using pydub."""
        if output_path is None:
            output_path = audio_path.replace(".wav", "_normalized.wav")

        audio = AudioSegment.from_wav(audio_path)

        # Normalize
        normalized = normalize(audio)

        # Adjust to target dB
        current_db = normalized.dBFS
        change = self.target_db - current_db
        normalized = normalized.apply_gain(change)

        normalized.export(output_path, format="wav")
        print(f"[Audio] Normalized: {current_db:.1f}dB -> {self.target_db:.1f}dB")
        return output_path

    def apply_fades(self, audio_path: str, output_path: str = None, 
                    fade_in_sec=None, fade_out_sec=None) -> str:
        """Apply fade in and fade out."""
        fade_in_sec = fade_in_sec or self.fade_in
        fade_out_sec = fade_out_sec or self.fade_out

        if output_path is None:
            output_path = audio_path.replace(".wav", "_faded.wav")

        audio = AudioSegment.from_wav(audio_path)

        # Apply fades
        audio = audio.fade_in(int(fade_in_sec * 1000))
        audio = audio.fade_out(int(fade_out_sec * 1000))

        audio.export(output_path, format="wav")
        print(f"[Audio] Applied fades: {fade_in_sec}s in, {fade_out_sec}s out")
        return output_path

    def mix_sound_effect(self, base_audio_path: str, effect_path: str, 
                         output_path: str = None, effect_volume_db=-10.0,
                         effect_start_ms=0) -> str:
        """Mix a sound effect into base audio at specific position."""
        if output_path is None:
            output_path = base_audio_path.replace(".wav", "_mixed.wav")

        base = AudioSegment.from_wav(base_audio_path)
        effect = AudioSegment.from_file(effect_path)

        # Adjust effect volume
        effect = effect + effect_volume_db

        # Overlay effect
        mixed = base.overlay(effect, position=effect_start_ms)

        mixed.export(output_path, format="wav")
        print(f"[Audio] Mixed effect at {effect_start_ms}ms")
        return output_path

    def mix_multiple_effects(self, base_audio_path: str, effects: list, 
                             output_path: str = None) -> str:
        """
        Mix multiple sound effects.
        effects: list of dicts with keys: path, volume_db, start_ms
        """
        if output_path is None:
            output_path = base_audio_path.replace(".wav", "_effects.wav")

        base = AudioSegment.from_wav(base_audio_path)

        for eff in effects:
            effect = AudioSegment.from_file(eff["path"])
            effect = effect + eff.get("volume_db", -10)
            base = base.overlay(effect, position=eff.get("start_ms", 0))

        base.export(output_path, format="wav")
        print(f"[Audio] Mixed {len(effects)} effects")
        return output_path

    def add_background_music(self, audio_path: str, music_path: str,
                            output_path: str = None, music_volume_db=-20.0,
                            ducking=True, duck_threshold_db=-30.0) -> str:
        """
        Add background music with optional ducking (volume reduction when voice/game audio is present).
        """
        if output_path is None:
            output_path = audio_path.replace(".wav", "_music.wav")

        base = AudioSegment.from_wav(audio_path)
        music = AudioSegment.from_file(music_path)

        # Loop music if shorter than base
        while len(music) < len(base):
            music += music
        music = music[:len(base)]

        # Apply volume
        music = music + music_volume_db

        if ducking:
            # Simple ducking: reduce music during loud parts
            # This is a simplified version - full implementation would use sidechain compression
            music = music - 6  # Slight reduction

        mixed = base.overlay(music)
        mixed.export(output_path, format="wav")
        print(f"[Audio] Added background music at {music_volume_db}dB")
        return output_path

    def process_clip_audio(self, audio_path: str, start_time: float, 
                           end_time: float, output_path: str = None,
                           add_kill_sound: bool = False,
                           add_music: bool = False,
                           music_path: str = None) -> str:
        """
        Full audio processing pipeline for a single clip.
        Cuts, normalizes, fades, optionally adds effects.
        """
        if output_path is None:
            output_path = audio_path.replace(".wav", f"_clip_{start_time:.1f}.wav")

        audio = AudioSegment.from_wav(audio_path)

        # Cut segment
        start_ms = int(start_time * 1000)
        end_ms = int(end_time * 1000)
        clip = audio[start_ms:end_ms]

        # Normalize
        clip = normalize(clip)
        current_db = clip.dBFS
        change = self.target_db - current_db
        clip = clip.apply_gain(change)

        # Apply fades
        clip = clip.fade_in(int(self.fade_in * 1000))
        clip = clip.fade_out(int(self.fade_out * 1000))

        # Add kill confirmation sound if requested
        if add_kill_sound:
            kill_sound_path = os.path.join(os.path.dirname(__file__), "../../assets/sound_effects/kill_confirm.wav")
            if os.path.exists(kill_sound_path):
                kill_sound = AudioSegment.from_file(kill_sound_path)
                kill_sound = kill_sound - 8  # Slightly lower volume
                clip = clip.overlay(kill_sound, position=0)

        # Add music if requested
        if add_music and music_path and os.path.exists(music_path):
            music = AudioSegment.from_file(music_path)
            while len(music) < len(clip):
                music += music
            music = music[:len(clip)]
            music = music - 22  # Background level
            clip = clip.overlay(music)

        clip.export(output_path, format="wav")
        print(f"[Audio] Processed clip audio: {start_time:.1f}s - {end_time:.1f}s")
        return output_path

    def get_audio_features(self, audio_path: str) -> dict:
        """Extract audio features for sync detection."""
        y, sr = librosa.load(audio_path, sr=self.sample_rate, mono=True)

        features = {
            "duration": len(y) / sr,
            "rms": float(np.mean(librosa.feature.rms(y=y)[0])),
            "spectral_centroid": float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)[0])),
            "zero_crossing_rate": float(np.mean(librosa.feature.zero_crossing_rate(y=y)[0]))
        }

        return features
