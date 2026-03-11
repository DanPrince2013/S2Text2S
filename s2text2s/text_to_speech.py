"""
Text-to-Speech with character-voice detection.

Features
--------
- Narrate plain text with the default system voice (pyttsx3 / SAPI5).
- Detect named-character dialogue in script and novel formats.
- Each character automatically receives a consistent voice profile
  (rate offset, volume variation) derived from their name hash.
- When multiple SAPI5 voices are installed different characters use
  different voices.

Supported character-dialogue patterns
--------------------------------------
Script:     ``CHARACTER_NAME: some dialogue text``
Novel A:    ``"dialogue," said/asked/replied/whispered/shouted Character``
Novel B:    ``Character said/asked/replied "dialogue"``
"""

from __future__ import annotations

import hashlib
import logging
import re
import threading
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

try:
    import pyttsx3  # type: ignore

    _HAS_TTS = True
except ImportError:
    _HAS_TTS = False

# ── Segment types ─────────────────────────────────────────────────────────────

NARRATOR = "__narrator__"

# Speech verbs used in dialogue attribution
_SPEECH_VERBS = (
    "said", "asked", "replied", "whispered", "shouted", "exclaimed",
    "answered", "muttered", "called", "cried", "demanded", "stated",
    "announced", "continued", "added", "agreed", "argued", "explained",
    "noted", "observed", "suggested",
)
_SPEECH_VERB_PAT = "|".join(_SPEECH_VERBS)


@dataclass
class _Segment:
    character: str   # NARRATOR or character name (lower-cased)
    text: str


# ── Character detection ───────────────────────────────────────────────────────

# Script format: "NAME:" or "NAME (stage direction):"
_SCRIPT_LINE = re.compile(
    r"^([A-Z][A-Z0-9 _\-']{0,30})(?:\s*\([^)]*\))?\s*:\s*(.+)$",
    re.MULTILINE,
)

# Novel format A: "dialogue" said/asked … Name
_NOVEL_A = re.compile(
    r'"([^"]+?)"\s*,?\s*(?:' + _SPEECH_VERB_PAT + r')\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)',
    re.DOTALL,
)

# Novel format B: Name said/asked … "dialogue"
_NOVEL_B = re.compile(
    r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:' + _SPEECH_VERB_PAT + r')[^"]*?"([^"]+?)"',
    re.DOTALL,
)


def parse_segments(text: str) -> List[_Segment]:
    """
    Split *text* into a list of :class:`_Segment` objects, each tagged with
    a character name (or :data:`NARRATOR`).
    """
    segments: List[_Segment] = []

    # ── Script format (line-by-line) ──────────────────────────────────────────
    # If we find at least one script-format line, treat the whole block as script
    if _SCRIPT_LINE.search(text):
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = _SCRIPT_LINE.match(line)
            if m:
                segments.append(
                    _Segment(character=m.group(1).strip().lower(), text=m.group(2).strip())
                )
            else:
                segments.append(_Segment(character=NARRATOR, text=line))
        return segments

    # ── Novel / prose format ──────────────────────────────────────────────────
    # Walk through the text finding dialogue spans and attribution
    pos = 0
    found_any = False

    # Collect all matches from both patterns, sort by start position
    matches: List[Tuple[int, int, str, str]] = []  # (start, end, character, dialogue)

    for m in _NOVEL_A.finditer(text):
        matches.append((m.start(), m.end(), m.group(2), m.group(1)))

    for m in _NOVEL_B.finditer(text):
        matches.append((m.start(), m.end(), m.group(1), m.group(2)))

    matches.sort(key=lambda x: x[0])

    for start, end, character, dialogue in matches:
        found_any = True
        # Text before this dialogue span → narrator
        narrator_text = text[pos:start].strip()
        if narrator_text:
            segments.append(_Segment(character=NARRATOR, text=narrator_text))
        segments.append(_Segment(character=character.lower(), text=dialogue.strip()))
        pos = end

    # Remaining text → narrator (also covers "no matches found" case)
    tail = text[pos:].strip()
    if tail:
        segments.append(_Segment(character=NARRATOR, text=tail))

    return [s for s in segments if s.text]


# ── Voice profile assignment ──────────────────────────────────────────────────

@dataclass
class VoiceProfile:
    rate_offset: int = 0
    volume: float = 0.9
    voice_index: int = 0


def _profile_for_character(
    name: str,
    available_voice_count: int,
    user_profiles: Optional[Dict[str, "VoiceProfile"]] = None,
) -> VoiceProfile:
    """
    Return a :class:`VoiceProfile` for *name*, using a deterministic hash so
    the same character always gets the same voice.
    """
    if user_profiles and name in user_profiles:
        return user_profiles[name]

    digest = int(hashlib.md5(name.encode()).hexdigest(), 16)
    # Rate offset: -25 … +25 WPM (11 values in steps of 5)
    rate_offset = ((digest % 11) - 5) * 5
    # Volume: 0.75 … 1.0
    volume = 0.75 + ((digest >> 4) % 6) * 0.05
    # Voice index: cycle through available voices (skip index 0 = narrator default)
    if available_voice_count <= 1:
        voice_index = 0
    else:
        voice_index = 1 + ((digest >> 8) % (available_voice_count - 1))

    return VoiceProfile(rate_offset=rate_offset, volume=volume, voice_index=voice_index)


# ── TTS engine ────────────────────────────────────────────────────────────────

class TextToSpeech:
    """
    Reads text aloud using pyttsx3 (SAPI5 on Windows).

    Parameters
    ----------
    base_rate:
        Default speaking rate in words-per-minute.
    base_volume:
        Default speaking volume (0.0 – 1.0).
    detect_characters:
        When ``True``, dialogue attribution is parsed and character voices
        are applied.
    user_voice_profiles:
        Optional per-character overrides (character name → :class:`VoiceProfile`).
    """

    def __init__(
        self,
        base_rate: int = 180,
        base_volume: float = 0.9,
        detect_characters: bool = True,
        user_voice_profiles: Optional[Dict[str, VoiceProfile]] = None,
    ) -> None:
        if not _HAS_TTS:
            raise RuntimeError(
                "pyttsx3 is required for TTS. "
                "Install it with: pip install pyttsx3"
            )
        self.base_rate = base_rate
        self.base_volume = base_volume
        self.detect_characters = detect_characters
        self.user_voice_profiles = user_voice_profiles or {}

        self._engine = pyttsx3.init()
        self._voices: list = self._engine.getProperty("voices") or []
        self._stop_event = threading.Event()

    # ── Public API ────────────────────────────────────────────────────────────

    def speak(self, text: str) -> None:
        """
        Speak *text* synchronously, blocking until finished or :meth:`stop`
        is called.
        """
        self._stop_event.clear()
        if not text.strip():
            return

        if self.detect_characters:
            segments = parse_segments(text)
        else:
            segments = [_Segment(character=NARRATOR, text=text)]

        for segment in segments:
            if self._stop_event.is_set():
                break
            self._speak_segment(segment)

        self._engine.runAndWait()

    def stop(self) -> None:
        """Interrupt any ongoing speech."""
        self._stop_event.set()
        try:
            self._engine.stop()
        except Exception:
            pass

    def speak_async(self, text: str) -> threading.Thread:
        """Start speaking in a background thread; returns the thread."""
        t = threading.Thread(target=self.speak, args=(text,), daemon=True)
        t.start()
        return t

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _speak_segment(self, segment: _Segment) -> None:
        if segment.character == NARRATOR:
            self._apply_voice(self.base_rate, self.base_volume, 0)
        else:
            profile = _profile_for_character(
                segment.character,
                len(self._voices),
                self.user_voice_profiles,  # type: ignore[arg-type]
            )
            rate = max(80, min(350, self.base_rate + profile.rate_offset))
            self._apply_voice(rate, profile.volume, profile.voice_index)

        self._engine.say(segment.text)

    def _apply_voice(self, rate: int, volume: float, voice_index: int) -> None:
        self._engine.setProperty("rate", rate)
        self._engine.setProperty("volume", volume)
        if self._voices and voice_index < len(self._voices):
            self._engine.setProperty("voice", self._voices[voice_index].id)
