"""
Configuration for S2Text2S.

All settings can be overridden by creating a file called ``s2text2s.cfg``
(INI format) in the current working directory.  For example::

    [hotkeys]
    stt_hotkey = right ctrl
    tts_hotkey = right alt

    [stt]
    engine = google

    [tts]
    rate = 180
    volume = 0.9

    [cleanup]
    remove_fillers = true
"""

import configparser
import os
from dataclasses import dataclass, field
from typing import Dict, List

_CFG_FILE = "s2text2s.cfg"


@dataclass
class CharacterVoiceProfile:
    """Voice properties for a single named character."""

    rate_offset: int = 0     # WPM delta from base rate
    volume: float = 0.9
    voice_index: int = 0     # Index into the available SAPI5 voices list


@dataclass
class Config:
    # ── Hotkeys ──────────────────────────────────────────────────────────────
    # Hold to record; release to transcribe & inject.
    stt_hotkey: str = "right ctrl"
    # Press once to read the currently selected text aloud.
    tts_hotkey: str = "right alt"

    # ── Speech-to-Text ───────────────────────────────────────────────────────
    stt_engine: str = "google"   # 'google' | 'azure' | 'sphinx'
    azure_key: str = ""
    azure_region: str = "eastus"

    # ── Text cleanup ─────────────────────────────────────────────────────────
    remove_fillers: bool = True
    filler_words: List[str] = field(default_factory=lambda: [
        "um", "uh", "you know", "like", "basically", "literally",
        "actually", "so like", "i mean", "right",
    ])

    # ── Text-to-Speech ───────────────────────────────────────────────────────
    tts_rate: int = 180          # base words-per-minute
    tts_volume: float = 0.9
    detect_characters: bool = True

    # Map of lower-cased character name → voice profile.
    # Populated dynamically for new characters; users can pre-fill via config.
    character_voices: Dict[str, CharacterVoiceProfile] = field(
        default_factory=dict
    )

    # ── Misc ─────────────────────────────────────────────────────────────────
    show_notifications: bool = True
    # Milliseconds of silence that split a "hold-to-record" chunk
    silence_threshold_ms: int = 500


def load_config(path: str = _CFG_FILE) -> Config:
    """Load a :class:`Config` from an INI file, falling back to defaults."""
    cfg = Config()
    if not os.path.exists(path):
        return cfg

    parser = configparser.ConfigParser()
    parser.read(path)

    if "hotkeys" in parser:
        sec = parser["hotkeys"]
        cfg.stt_hotkey = sec.get("stt_hotkey", cfg.stt_hotkey)
        cfg.tts_hotkey = sec.get("tts_hotkey", cfg.tts_hotkey)

    if "stt" in parser:
        sec = parser["stt"]
        cfg.stt_engine = sec.get("engine", cfg.stt_engine)
        cfg.azure_key = sec.get("azure_key", cfg.azure_key)
        cfg.azure_region = sec.get("azure_region", cfg.azure_region)

    if "tts" in parser:
        sec = parser["tts"]
        cfg.tts_rate = sec.getint("rate", cfg.tts_rate)
        cfg.tts_volume = sec.getfloat("volume", cfg.tts_volume)
        cfg.detect_characters = sec.getboolean(
            "detect_characters", cfg.detect_characters
        )

    if "cleanup" in parser:
        sec = parser["cleanup"]
        cfg.remove_fillers = sec.getboolean("remove_fillers", cfg.remove_fillers)
        raw = sec.get("filler_words", "")
        if raw:
            cfg.filler_words = [w.strip() for w in raw.split(",") if w.strip()]

    if "characters" in parser:
        for name, value in parser["characters"].items():
            parts = [p.strip() for p in value.split(",")]
            rate_offset = int(parts[0]) if len(parts) > 0 else 0
            volume = float(parts[1]) if len(parts) > 1 else 0.9
            voice_index = int(parts[2]) if len(parts) > 2 else 0
            cfg.character_voices[name.lower()] = CharacterVoiceProfile(
                rate_offset=rate_offset,
                volume=volume,
                voice_index=voice_index,
            )

    return cfg
