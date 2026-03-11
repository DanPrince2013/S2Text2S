"""
Audio recorder using sounddevice.

Records microphone input into a numpy array while the caller's event is set,
then converts to a WAV-compatible bytes buffer for SpeechRecognition.
"""

import io
import threading
from typing import Optional

import numpy as np

try:
    import sounddevice as sd  # type: ignore
    import scipy.io.wavfile as wav  # type: ignore

    _HAS_AUDIO = True
except ImportError:
    _HAS_AUDIO = False


_SAMPLE_RATE = 16_000   # Hz — matches what most STT engines prefer
_CHANNELS = 1
_DTYPE = "int16"


class AudioRecorder:
    """
    Thread-safe microphone recorder.

    Usage::

        recorder = AudioRecorder()
        recorder.start()
        # … user speaks …
        audio_bytes = recorder.stop()   # WAV bytes
    """

    def __init__(self, sample_rate: int = _SAMPLE_RATE) -> None:
        if not _HAS_AUDIO:
            raise RuntimeError(
                "sounddevice and scipy are required for audio recording. "
                "Install them with: pip install sounddevice scipy"
            )
        self.sample_rate = sample_rate
        self._frames: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional["sd.InputStream"] = None

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self) -> None:
        """Begin capturing audio from the default input device."""
        with self._lock:
            if self._stream is not None:
                return  # already recording
            self._frames = []
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=_CHANNELS,
                dtype=_DTYPE,
                callback=self._callback,
            )
            self._stream.start()

    def stop(self) -> Optional[bytes]:
        """
        Stop recording and return the captured audio as WAV bytes.
        Returns ``None`` if nothing was recorded.
        """
        with self._lock:
            if self._stream is None:
                return None
            self._stream.stop()
            self._stream.close()
            self._stream = None
            frames = self._frames.copy()

        if not frames:
            return None

        audio = np.concatenate(frames, axis=0).flatten()
        buf = io.BytesIO()
        wav.write(buf, self.sample_rate, audio)
        return buf.getvalue()

    @property
    def is_recording(self) -> bool:
        return self._stream is not None

    # ── Internal ──────────────────────────────────────────────────────────────

    def _callback(
        self,
        indata: np.ndarray,
        frames: int,
        time,
        status,
    ) -> None:
        with self._lock:
            self._frames.append(indata.copy())
