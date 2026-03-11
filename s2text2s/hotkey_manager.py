"""
Hotkey manager.

Registers global hotkeys and dispatches to callbacks:

- **Right Ctrl** (hold to record, release to transcribe + inject)
- **Right Alt** (press to read selected text aloud)
- **Escape** (press to stop ongoing TTS playback)

Both hotkeys can be reconfigured via :class:`~s2text2s.config.Config`.
"""

from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

try:
    import keyboard  # type: ignore

    _HAS_KBD = True
except ImportError:
    _HAS_KBD = False


class HotkeyManager:
    """
    Registers OS-level hotkeys and forwards events to caller-supplied
    callbacks.

    Parameters
    ----------
    stt_hotkey:
        Key name for speech-to-text (e.g. ``'right ctrl'``).
    tts_hotkey:
        Key name for text-to-speech (e.g. ``'right alt'``).
    on_stt_start:
        Called when *stt_hotkey* is pressed (begin recording).
    on_stt_stop:
        Called when *stt_hotkey* is released (stop recording, transcribe).
    on_tts_trigger:
        Called when *tts_hotkey* is pressed (read selected text).
    on_stop_tts:
        Called when ``Escape`` is pressed (stop playback).
    """

    def __init__(
        self,
        stt_hotkey: str = "right ctrl",
        tts_hotkey: str = "right alt",
        on_stt_start: Optional[Callable[[], None]] = None,
        on_stt_stop: Optional[Callable[[], None]] = None,
        on_tts_trigger: Optional[Callable[[], None]] = None,
        on_stop_tts: Optional[Callable[[], None]] = None,
    ) -> None:
        if not _HAS_KBD:
            raise RuntimeError(
                "keyboard is required for hotkey management. "
                "Install it with: pip install keyboard"
            )
        self.stt_hotkey = stt_hotkey
        self.tts_hotkey = tts_hotkey
        self._on_stt_start = on_stt_start or (lambda: None)
        self._on_stt_stop = on_stt_stop or (lambda: None)
        self._on_tts_trigger = on_tts_trigger or (lambda: None)
        self._on_stop_tts = on_stop_tts or (lambda: None)
        self._active = False
        self._stt_pressed = False

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Register all hotkeys and begin listening."""
        if self._active:
            return
        self._active = True

        keyboard.on_press_key(self.stt_hotkey, self._handle_stt_press, suppress=True)
        keyboard.on_release_key(self.stt_hotkey, self._handle_stt_release, suppress=True)

        keyboard.on_press_key(self.tts_hotkey, self._handle_tts_press, suppress=True)

        keyboard.on_press_key("escape", self._handle_escape)

        logger.info(
            "Hotkeys active — STT: %s | TTS: %s | Stop: Escape",
            self.stt_hotkey,
            self.tts_hotkey,
        )

    def stop(self) -> None:
        """Unregister all hotkeys."""
        if not self._active:
            return
        self._active = False
        try:
            keyboard.unhook_all()
        except Exception:
            pass

    # ── Internal callbacks ────────────────────────────────────────────────────

    def _handle_stt_press(self, event) -> None:
        if not self._stt_pressed:
            self._stt_pressed = True
            _dispatch(self._on_stt_start)

    def _handle_stt_release(self, event) -> None:
        if self._stt_pressed:
            self._stt_pressed = False
            _dispatch(self._on_stt_stop)

    def _handle_tts_press(self, event) -> None:
        _dispatch(self._on_tts_trigger)

    def _handle_escape(self, event) -> None:
        _dispatch(self._on_stop_tts)


def _dispatch(fn: Callable[[], None]) -> None:
    """Call *fn* in a daemon thread so hotkey callbacks don't block."""
    threading.Thread(target=fn, daemon=True).start()
