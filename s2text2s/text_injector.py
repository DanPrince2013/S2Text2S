"""
Text injector — pastes text into whatever field currently has focus.

Strategy
--------
1. Save the current clipboard content.
2. Copy the new text to the clipboard.
3. Simulate Ctrl+V (paste).
4. Restore the original clipboard content after a short delay.

This approach works with virtually every Windows application because it
relies on the OS paste mechanism rather than synthesising individual key
events.

On non-Windows platforms the module falls back to pyperclip + keyboard so
that unit tests can import it without errors.
"""

from __future__ import annotations

import logging
import platform
import time

logger = logging.getLogger(__name__)

try:
    import pyperclip  # type: ignore

    _HAS_CLIP = True
except ImportError:
    _HAS_CLIP = False

try:
    import keyboard  # type: ignore

    _HAS_KBD = True
except ImportError:
    _HAS_KBD = False


_IS_WINDOWS = platform.system() == "Windows"

# Seconds to wait between clipboard operations
_PASTE_DELAY = 0.05
# Seconds before restoring the old clipboard content
_RESTORE_DELAY = 0.5


class TextInjectorError(Exception):
    """Raised when injection cannot be performed."""


class TextInjector:
    """
    Inject text into the currently focused text field.

    Parameters
    ----------
    restore_clipboard:
        When ``True`` (default), the original clipboard content is restored
        after pasting.  Set to ``False`` if you want the injected text to
        remain on the clipboard.
    """

    def __init__(self, restore_clipboard: bool = True) -> None:
        if not _HAS_CLIP:
            raise RuntimeError(
                "pyperclip is required for text injection. "
                "Install it with: pip install pyperclip"
            )
        if not _HAS_KBD:
            raise RuntimeError(
                "keyboard is required for text injection. "
                "Install it with: pip install keyboard"
            )
        self.restore_clipboard = restore_clipboard

    # ── Public API ────────────────────────────────────────────────────────────

    def inject(self, text: str) -> None:
        """
        Inject *text* at the current cursor position.

        The method saves and (optionally) restores the clipboard so the
        user's copy buffer is not permanently overwritten.

        Raises
        ------
        TextInjectorError
            When clipboard or keyboard access fails.
        """
        if not text:
            return

        try:
            original = pyperclip.paste()
        except Exception:
            original = ""

        try:
            pyperclip.copy(text)
            time.sleep(_PASTE_DELAY)
            keyboard.send("ctrl+v")
            time.sleep(_PASTE_DELAY)
        except Exception as exc:
            raise TextInjectorError(f"Failed to inject text: {exc}") from exc
        finally:
            if self.restore_clipboard:
                time.sleep(_RESTORE_DELAY)
                try:
                    pyperclip.copy(original)
                except Exception:
                    pass


def get_selected_text() -> str:
    """
    Attempt to retrieve the currently selected text by simulating Ctrl+C.

    The original clipboard content is saved and restored so that the user's
    copy buffer is not permanently overwritten.

    Returns an empty string when nothing is selected or clipboard access fails.
    """
    if not _HAS_CLIP or not _HAS_KBD:
        return ""

    try:
        original = pyperclip.paste()
    except Exception:
        original = ""

    try:
        pyperclip.copy("")
        time.sleep(_PASTE_DELAY)
        keyboard.send("ctrl+c")
        time.sleep(_PASTE_DELAY * 4)  # Allow the app to populate the clipboard
        selected = pyperclip.paste()
    except Exception:
        selected = ""

    try:
        pyperclip.copy(original)
    except Exception:
        pass

    return selected if selected != original else ""
