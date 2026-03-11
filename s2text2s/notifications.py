"""
Notification helper.

Shows a brief desktop notification on Windows (via win10toast if available,
with a fallback to a simple print message).
"""

from __future__ import annotations

import logging
import platform

logger = logging.getLogger(__name__)

_IS_WINDOWS = platform.system() == "Windows"

try:
    from win10toast import ToastNotifier  # type: ignore

    _toast = ToastNotifier()
    _HAS_TOAST = True
except ImportError:
    _HAS_TOAST = False


def notify(title: str, message: str, duration: int = 3) -> None:
    """
    Display a desktop notification.

    Falls back gracefully on non-Windows platforms or when win10toast is not
    installed.

    Parameters
    ----------
    title:
        Notification title.
    message:
        Notification body.
    duration:
        How long (seconds) to show the notification.
    """
    logger.debug("Notification: %s — %s", title, message)
    if _IS_WINDOWS and _HAS_TOAST:
        try:
            _toast.show_toast(
                title,
                message,
                duration=duration,
                threaded=True,
            )
            return
        except Exception as exc:
            logger.debug("Toast notification failed: %s", exc)

    # Fallback: print to console
    print(f"[{title}] {message}")
