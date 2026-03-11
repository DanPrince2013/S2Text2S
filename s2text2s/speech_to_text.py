"""
Speech-to-Text wrapper.

Supports:
- Google Web Speech API (default, requires internet)
- Microsoft Azure Cognitive Services Speech (requires key/region)
- CMU Sphinx (offline, lower accuracy)

The engine is selected via :class:`~s2text2s.config.Config`.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import speech_recognition as sr  # type: ignore

    _HAS_SR = True
except ImportError:
    _HAS_SR = False


class SpeechToTextError(Exception):
    """Raised when transcription fails for a recoverable reason."""


class SpeechToText:
    """
    Thin wrapper around *SpeechRecognition* that accepts raw WAV bytes and
    returns a transcript string.

    Parameters
    ----------
    engine:
        One of ``'google'``, ``'azure'``, or ``'sphinx'``.
    azure_key:
        Required when *engine* is ``'azure'``.
    azure_region:
        Azure region string (e.g. ``'eastus'``).
    """

    def __init__(
        self,
        engine: str = "google",
        azure_key: str = "",
        azure_region: str = "eastus",
    ) -> None:
        if not _HAS_SR:
            raise RuntimeError(
                "SpeechRecognition is required. "
                "Install it with: pip install SpeechRecognition"
            )
        self.engine = engine.lower()
        self.azure_key = azure_key
        self.azure_region = azure_region
        self._recognizer = sr.Recognizer()

    # ── Public API ────────────────────────────────────────────────────────────

    def transcribe(self, wav_bytes: bytes) -> str:
        """
        Transcribe *wav_bytes* (a complete WAV file in memory) and return
        the recognised text.

        Raises
        ------
        SpeechToTextError
            When speech is unintelligible or the service is unavailable.
        """
        import io

        audio_file = io.BytesIO(wav_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = self._recognizer.record(source)

        return self._recognise(audio_data)

    # ── Engine dispatch ───────────────────────────────────────────────────────

    def _recognise(self, audio: "sr.AudioData") -> str:
        try:
            if self.engine == "google":
                return self._recognizer.recognize_google(audio)
            elif self.engine == "azure":
                return self._recognizer.recognize_azure(
                    audio,
                    key=self.azure_key,
                    location=self.azure_region,
                )
            elif self.engine == "sphinx":
                return self._recognizer.recognize_sphinx(audio)
            else:
                raise ValueError(f"Unknown STT engine: {self.engine!r}")

        except Exception as exc:
            # Map SpeechRecognition exceptions to our own type
            name = type(exc).__name__
            if "UnknownValue" in name:
                raise SpeechToTextError("Speech not recognised.") from exc
            if "RequestError" in name:
                raise SpeechToTextError(
                    f"STT service unavailable: {exc}"
                ) from exc
            raise
