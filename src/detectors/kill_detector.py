"""
COD Highlight Cutter v3.0 - Smart Kill & Death Detector
Uses: OCR + Audio + Frame Analysis + Multi-method fusion
"""
import cv2
import numpy as np
import pytesseract
import librosa
import soundfile as sf
from dataclasses import dataclass
from typing import List, Tuple, Optional
from collections import deque
import os
import json

@dataclass
class Event:
    timestamp: float
    event_type: str  # "kill", "death", "multikill", "headshot", "medal"
    confidence: float
    frame_data: dict = None

class SmartKillDeathDetector:
    """
    Multi-modal detector combining:
    1. OCR text detection (kill feed, medals)
    2. Audio spike detection (gunfire, explosions)
    3. Visual HUD analysis (crosshair, hit markers)
    4. Screen region analysis (kill cam, score popups)
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.kill_keywords = [
            "eliminated", "killed", "takedown", "downed", "defeated",
            "ELIMINATED", "KILLED", "TAKEDOWN", "DOWNED", "DEFEATED",
            "you killed", "you eliminated", "enemy down"
        ]
        self.death_keywords = [
            "killed by", "eliminated by", "defeated by", "you died",
            "KILLED BY", "ELIMINATED BY", "DEFEATED BY", "YOU DIED"
        ]
        self.medal_keywords = [
            "double kill", "triple kill", "quad kill", "fury kill",
            "ruthless", "merciless", "bloodthirsty", "nuclear",
            "DOUBLE KILL", "TRIPLE KILL", "QUAD KILL", "FURY KILL"
        ]
        self.headshot_keywords = ["headshot", "HEADSHOT", "head shot"]

        # Detection state
        self.recent_events = deque(maxlen=50)
        self.last_kill_time = -10.0
        self.last_death_time = -10.0
        self.consecutive_kills = 0
        self.kill_streak_start = 0.0

        # Audio state
        self.audio_buffer = deque(maxlen=100)
        self.last_audio_spike = -1.0

    def detect_from_video(self, video_path: str, audio_path: str = None) -> List[Event]:
        """Main entry: analyze entire video and return all events."""
        events = []

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0

        print(f"[Detector] Analyzing {total_frames} frames @ {fps:.1f}fps ({duration:.1f}s)")

        # Load audio for sync detection
        audio_events = []
        if audio_path and os.path.exists(audio_path):
            audio_events = self._analyze_audio(audio_path, fps)

        frame_idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            timestamp = frame_idx / fps

            # Run all detection methods
            ocr_events = self._detect_ocr(frame, timestamp)
            visual_events = self._detect_visual(frame, timestamp)

            # Fuse detections
            fused = self._fuse_detections(ocr_events, visual_events, audio_events, timestamp)
            events.extend(fused)

            # Progress
            if frame_idx % int(fps * 5) == 0:  # every 5 seconds
                pct = (frame_idx / total_frames) * 100
                print(f"[Detector] Progress: {pct:.1f}% ({frame_idx}/{total_frames})")

            frame_idx += 1

        cap.release()

        # Post-process: merge close events, filter false positives
        events = self._post_process(events)

        print(f"[Detector] Found {len(events)} events total")
        for e in events[:10]:
            print(f"  -> {e.event_type} @ {e.timestamp:.2f}s (conf: {e.confidence:.2f})")
        if len(events) > 10:
            print(f"  ... and {len(events)-10} more")

        return events

    def _detect_ocr(self, frame: np.ndarray, timestamp: float) -> List[Event]:
        """Detect kill/death text via OCR on specific screen regions."""
        events = []
        h, w = frame.shape[:2]

        # Define regions of interest for different game UIs
        regions = {
            "kill_feed": (int(w*0.65), 0, w, int(h*0.25)),           # Top-right kill feed
            "center_popup": (int(w*0.3), int(h*0.15), int(w*0.7), int(h*0.4)),  # Center medals
            "death_cam": (int(w*0.2), int(h*0.1), int(w*0.8), int(h*0.5)),     # Kill cam text
            "scoreboard": (0, 0, w, int(h*0.15)),                     # Top score info
        }

        for region_name, (x1, y1, x2, y2) in regions.items():
            roi = frame[y1:y2, x1:x2]
            if roi.size == 0:
                continue

            # Preprocess for OCR
            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # OCR with specific config for game text
            text = pytesseract.image_to_string(binary, config="--psm 6 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 ").lower()

            # Check for keywords
            for keyword in self.kill_keywords:
                if keyword in text:
                    conf = self._calculate_ocr_confidence(text, keyword)
                    events.append(Event(timestamp, "kill", conf, {"region": region_name, "text": text[:100]}))
                    break

            for keyword in self.death_keywords:
                if keyword in text:
                    conf = self._calculate_ocr_confidence(text, keyword)
                    events.append(Event(timestamp, "death", conf, {"region": region_name, "text": text[:100]}))
                    break

            for keyword in self.medal_keywords:
                if keyword in text:
                    conf = self._calculate_ocr_confidence(text, keyword)
                    medal_type = keyword.replace(" ", "_")
                    events.append(Event(timestamp, f"medal_{medal_type}", conf, {"region": region_name}))
                    break

            for keyword in self.headshot_keywords:
                if keyword in text:
                    events.append(Event(timestamp, "headshot", 0.85, {"region": region_name}))
                    break

        return events

    def _detect_visual(self, frame: np.ndarray, timestamp: float) -> List[Event]:
        """Detect visual cues: hit markers, screen flash, crosshair changes."""
        events = []
        h, w = frame.shape[:2]

        # Center region for hit marker detection
        center_x, center_y = w // 2, h // 2
        center_roi = frame[center_y-30:center_y+30, center_x-30:center_x+30]

        if center_roi.size > 0:
            # Detect red/white hit markers (common in CoD)
            hsv = cv2.cvtColor(center_roi, cv2.COLOR_BGR2HSV)

            # Red hit marker detection
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([160, 100, 100])
            upper_red2 = np.array([180, 255, 255])

            red_mask = cv2.inRange(hsv, lower_red1, upper_red1) + cv2.inRange(hsv, lower_red2, upper_red2)
            red_ratio = np.sum(red_mask > 0) / red_mask.size

            if red_ratio > 0.15:  # Significant red in center
                events.append(Event(timestamp, "hit_marker", red_ratio, {"type": "red", "ratio": red_ratio}))

            # White crosshair hit detection
            gray_center = cv2.cvtColor(center_roi, cv2.COLOR_BGR2GRAY)
            white_mask = gray_center > 240
            white_ratio = np.sum(white_mask) / white_mask.size

            if white_ratio > 0.1:
                events.append(Event(timestamp, "hit_marker", white_ratio * 0.8, {"type": "white", "ratio": white_ratio}))

        # Screen flash detection (death/respawn)
        avg_brightness = np.mean(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
        if avg_brightness > 230:  # Very bright screen
            events.append(Event(timestamp, "screen_flash", 0.7, {"brightness": avg_brightness}))

        # Kill cam border detection (darkened edges)
        edge_darkness = np.mean(frame[:20, :]) + np.mean(frame[-20:, :]) + np.mean(frame[:, :20]) + np.mean(frame[:, -20:])
        edge_darkness /= 4
        if edge_darkness < 40:
            events.append(Event(timestamp, "kill_cam", 0.6, {"edge_darkness": edge_darkness}))

        return events

    def _analyze_audio(self, audio_path: str, video_fps: float) -> List[Tuple[float, float, str]]:
        """Analyze audio for gunshots, explosions, and kill confirmation sounds."""
        print(f"[Audio] Analyzing {audio_path}")

        y, sr = librosa.load(audio_path, sr=None, mono=True)
        duration = len(y) / sr

        # Frame-level analysis
        hop_length = int(sr / video_fps)  # Sync with video frames
        if hop_length < 512:
            hop_length = 512

        # Onset detection for gunshots/explosions
        onset_env = librosa.onset.onset_strength(y=y, sr=sr, hop_length=hop_length)
        onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env, sr=sr, hop_length=hop_length)

        # Spectral features for sound classification
        spectral_centroid = librosa.feature.spectral_centroid(y=y, sr=sr, hop_length=hop_length)[0]
        spectral_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr, hop_length=hop_length)[0]
        rms = librosa.feature.rms(y=y, hop_length=hop_length)[0]

        audio_events = []

        for onset in onset_frames:
            time = onset * hop_length / sr

            # Classify sound type based on spectral features
            sc = spectral_centroid[min(onset, len(spectral_centroid)-1)]
            sr_val = spectral_rolloff[min(onset, len(spectral_rolloff)-1)]
            rms_val = rms[min(onset, len(rms)-1)]

            if rms_val > 0.3:  # Loud sound
                if sc > 4000 and sr_val > 8000:
                    sound_type = "gunshot_high"
                elif sc > 2000:
                    sound_type = "gunshot_mid"
                elif sr_val < 3000:
                    sound_type = "explosion"
                else:
                    sound_type = "loud_impact"

                audio_events.append((time, rms_val, sound_type))

        print(f"[Audio] Detected {len(audio_events)} audio events")
        return audio_events

    def _fuse_detections(self, ocr_events, visual_events, audio_events, timestamp, 
                         window=0.5) -> List[Event]:
        """Fuse multi-modal detections within time window."""
        fused = []

        # Group OCR events by type
        ocr_kills = [e for e in ocr_events if e.event_type == "kill"]
        ocr_deaths = [e for e in ocr_events if e.event_type == "death"]
        ocr_medals = [e for e in ocr_events if e.event_type.startswith("medal_")]

        # Check for kill confirmation (OCR + visual + audio)
        for ocr_kill in ocr_kills:
            conf = ocr_kill.confidence

            # Boost with visual hit marker
            visual_hits = [e for e in visual_events 
                          if e.event_type == "hit_marker" 
                          and abs(e.timestamp - ocr_kill.timestamp) < window]
            if visual_hits:
                conf = min(1.0, conf + 0.15)

            # Boost with audio
            audio_hits = [e for e in audio_events 
                         if abs(e[0] - ocr_kill.timestamp) < window and e[1] > 0.2]
            if audio_hits:
                conf = min(1.0, conf + 0.1)

            # Check for multikill
            if self.last_kill_time > 0 and (ocr_kill.timestamp - self.last_kill_time) < 4.0:
                self.consecutive_kills += 1
                if self.consecutive_kills >= 2:
                    fused.append(Event(ocr_kill.timestamp, f"multikill_x{self.consecutive_kills}", 
                                     min(1.0, conf + 0.1), {"streak": self.consecutive_kills}))
            else:
                self.consecutive_kills = 1
                self.kill_streak_start = ocr_kill.timestamp

            self.last_kill_time = ocr_kill.timestamp
            fused.append(Event(ocr_kill.timestamp, "kill", conf, ocr_kill.frame_data))

        # Check for death confirmation
        for ocr_death in ocr_deaths:
            conf = ocr_death.confidence

            # Boost with screen flash or kill cam
            visual_death = [e for e in visual_events 
                           if e.event_type in ["screen_flash", "kill_cam"]
                           and abs(e.timestamp - ocr_death.timestamp) < window]
            if visual_death:
                conf = min(1.0, conf + 0.15)

            self.last_death_time = ocr_death.timestamp
            self.consecutive_kills = 0
            fused.append(Event(ocr_death.timestamp, "death", conf, ocr_death.frame_data))

        # Add medals
        for medal in ocr_medals:
            fused.append(medal)

        # Add standalone headshots
        for vis in visual_events:
            if vis.event_type == "hit_marker" and not any(e.event_type == "kill" for e in ocr_kills):
                # Possible unconfirmed kill
                if vis.confidence > 0.6:
                    fused.append(Event(timestamp, "possible_kill", vis.confidence * 0.7, vis.frame_data))

        return fused

    def _post_process(self, events: List[Event]) -> List[Event]:
        """Merge duplicate events, filter false positives, sort."""
        if not events:
            return []

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)

        # Merge close events of same type
        merged = []
        for event in events:
            if not merged:
                merged.append(event)
                continue

            last = merged[-1]
            if event.event_type == last.event_type and abs(event.timestamp - last.timestamp) < 1.5:
                # Merge: keep higher confidence
                if event.confidence > last.confidence:
                    merged[-1] = event
            else:
                merged.append(event)

        # Filter by confidence threshold
        kill_death_events = [e for e in merged if e.event_type in ["kill", "death", "multikill_x2", "multikill_x3", "multikill_x4", "multikill_x5"]]

        # Require minimum confidence
        filtered = [e for e in kill_death_events if e.confidence >= 0.6]

        # Add back medals and special events
        special = [e for e in merged if e.event_type.startswith("medal_") or e.event_type == "headshot"]

        final = filtered + special
        final.sort(key=lambda e: e.timestamp)

        return final

    def _calculate_ocr_confidence(self, text: str, keyword: str) -> float:
        """Calculate confidence based on text clarity and keyword match."""
        base_conf = 0.7

        # Boost if keyword is exact match (not partial)
        if f" {keyword} " in f" {text} " or text.startswith(keyword) or text.endswith(keyword):
            base_conf += 0.1

        # Boost if text is short and clear (less noise)
        if len(text) < 50:
            base_conf += 0.05

        # Penalty if text has many non-alphanumeric chars
        special_ratio = sum(1 for c in text if not c.isalnum() and c != ' ') / max(len(text), 1)
        base_conf -= special_ratio * 0.2

        return max(0.5, min(1.0, base_conf))

    def export_events_json(self, events: List[Event], output_path: str):
        """Export events to JSON for debugging/review."""
        data = [{
            "timestamp": e.timestamp,
            "event_type": e.event_type,
            "confidence": e.confidence,
            "frame_data": e.frame_data
        } for e in events]

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"[Detector] Events exported to {output_path}")
