"""
S2Text2S — main application.

Wires together:

- :class:`~s2text2s.audio_recorder.AudioRecorder`
- :class:`~s2text2s.speech_to_text.SpeechToText`
- :class:`~s2text2s.text_cleaner.clean_transcript`
- :class:`~s2text2s.text_injector.TextInjector` / :func:`~s2text2s.text_injector.get_selected_text`
- :class:`~s2text2s.text_to_speech.TextToSpeech`
- :class:`~s2text2s.hotkey_manager.HotkeyManager`

System tray icon provides visual status and a quit option.
"""

from __future__ import annotations

import logging
import threading
from enum import Enum, auto
from typing import Optional

from s2text2s.audio_recorder import AudioRecorder
from s2text2s.config import Config, load_config
from s2text2s.hotkey_manager import HotkeyManager
from s2text2s.notifications import notify
from s2text2s.speech_to_text import SpeechToText, SpeechToTextError
from s2text2s.text_cleaner import clean_transcript
from s2text2s.text_injector import TextInjector, TextInjectorError, get_selected_text
from s2text2s.text_to_speech import TextToSpeech

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


class AppState(Enum):
    IDLE = auto()
    RECORDING = auto()
    PROCESSING = auto()


class App:
    """Top-level application controller."""

    def __init__(self, config: Optional[Config] = None) -> None:
        self.cfg = config or load_config()
        self._state = AppState.IDLE
        self._state_lock = threading.Lock()
        self._tts_thread: Optional[threading.Thread] = None

        # Lazily initialised components (to allow import without optional deps)
        self._recorder: Optional[AudioRecorder] = None
        self._stt: Optional[SpeechToText] = None
        self._tts: Optional[TextToSpeech] = None
        self._injector: Optional[TextInjector] = None
        self._hotkeys: Optional[HotkeyManager] = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Initialise components and start listening for hotkeys."""
        self._recorder = AudioRecorder()
        self._stt = SpeechToText(
            engine=self.cfg.stt_engine,
            azure_key=self.cfg.azure_key,
            azure_region=self.cfg.azure_region,
        )
        self._tts = TextToSpeech(
            base_rate=self.cfg.tts_rate,
            base_volume=self.cfg.tts_volume,
            detect_characters=self.cfg.detect_characters,
        )
        self._injector = TextInjector()
        self._hotkeys = HotkeyManager(
            stt_hotkey=self.cfg.stt_hotkey,
            tts_hotkey=self.cfg.tts_hotkey,
            on_stt_start=self._on_record_start,
            on_stt_stop=self._on_record_stop,
            on_tts_trigger=self._on_tts_trigger,
            on_stop_tts=self._on_stop_tts,
        )
        self._hotkeys.start()
        if self.cfg.show_notifications:
            notify(
                "S2Text2S",
                f"Ready.  Hold {self.cfg.stt_hotkey!r} to dictate • "
                f"{self.cfg.tts_hotkey!r} to read selection.",
            )
        logger.info("S2Text2S started.")

    def stop(self) -> None:
        """Shut down hotkeys and TTS gracefully."""
        if self._hotkeys:
            self._hotkeys.stop()
        if self._tts:
            self._tts.stop()
        logger.info("S2Text2S stopped.")

    def run_blocking(self) -> None:
        """
        Start the app and block the calling thread until interrupted.

        Suitable for running from the command line without a GUI event loop.
        """
        self.start()
        try:
            import keyboard  # type: ignore

            logger.info("Press Ctrl+C to exit.")
            keyboard.wait()
        except (ImportError, KeyboardInterrupt):
            pass
        finally:
            self.stop()

    # ── STT flow ──────────────────────────────────────────────────────────────

    def _on_record_start(self) -> None:
        with self._state_lock:
            if self._state != AppState.IDLE:
                return
            self._state = AppState.RECORDING

        logger.info("Recording started.")
        if self.cfg.show_notifications:
            notify("S2Text2S", "🎙 Recording…", duration=1)
        assert self._recorder is not None
        self._recorder.start()

    def _on_record_stop(self) -> None:
        with self._state_lock:
            if self._state != AppState.RECORDING:
                return
            self._state = AppState.PROCESSING

        logger.info("Recording stopped — transcribing…")
        assert self._recorder is not None
        wav_bytes = self._recorder.stop()

        if not wav_bytes:
            logger.warning("No audio captured.")
            with self._state_lock:
                self._state = AppState.IDLE
            return

        threading.Thread(target=self._transcribe_and_inject, args=(wav_bytes,), daemon=True).start()

    def _transcribe_and_inject(self, wav_bytes: bytes) -> None:
        try:
            assert self._stt is not None
            raw_text = self._stt.transcribe(wav_bytes)
            logger.info("Raw transcript: %r", raw_text)

            cleaned = clean_transcript(
                raw_text,
                fillers=self.cfg.filler_words,
                remove_fillers=self.cfg.remove_fillers,
            )
            logger.info("Cleaned text: %r", cleaned)

            assert self._injector is not None
            self._injector.inject(cleaned)

            if self.cfg.show_notifications:
                preview = cleaned[:60] + ("…" if len(cleaned) > 60 else "")
                notify("S2Text2S", f"✓ Injected: {preview}")

        except SpeechToTextError as exc:
            logger.warning("STT error: %s", exc)
            if self.cfg.show_notifications:
                notify("S2Text2S", f"⚠ {exc}")

        except TextInjectorError as exc:
            logger.error("Injection error: %s", exc)
            if self.cfg.show_notifications:
                notify("S2Text2S", f"✗ Injection failed: {exc}")

        except Exception as exc:
            logger.exception("Unexpected error during transcription: %s", exc)

        finally:
            with self._state_lock:
                self._state = AppState.IDLE

    # ── TTS flow ──────────────────────────────────────────────────────────────

    def _on_tts_trigger(self) -> None:
        text = get_selected_text()
        if not text.strip():
            logger.info("No text selected; nothing to read.")
            return

        logger.info("Reading %d chars.", len(text))
        assert self._tts is not None
        # Stop any ongoing TTS first
        self._tts.stop()
        self._tts_thread = self._tts.speak_async(text)

    def _on_stop_tts(self) -> None:
        if self._tts:
            self._tts.stop()
            logger.info("TTS stopped.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    app = App()
    app.run_blocking()


if __name__ == "__main__":
    main()
