"""Deliver text into the frontmost app: clipboard swap + simulated Cmd+V.

Pasting is far more reliable than synthetic per-character typing (IME apps,
Electron, and terminals all handle it), and it's what Wispr Flow does too.
The user's clipboard is restored afterwards no matter what — unless delivery
itself fails, in which case the transcript stays on the clipboard so it isn't
lost (macOS drops synthetic keystrokes silently without Accessibility).
"""

import ctypes
import logging
import time

import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString

log = logging.getLogger(__name__)

KEY_V = 9  # kVK_ANSI_V
# How long the target app gets to read the pasteboard before we restore it.
PASTE_SETTLE_SECONDS = 0.25

_app_services = ctypes.cdll.LoadLibrary(
    "/System/Library/Frameworks/ApplicationServices.framework/ApplicationServices"
)


def is_trusted() -> bool:
    """Whether macOS will accept our synthetic keystrokes (Accessibility)."""
    return bool(_app_services.AXIsProcessTrusted())


def paste_text(text: str) -> bool:
    """Paste text into the frontmost app. Returns True if delivery happened.

    Without Accessibility the ⌘V never lands, so the transcript is left on the
    clipboard as fallback delivery — the one case we don't restore it.
    """
    pb = NSPasteboard.generalPasteboard()
    if not is_trusted():
        pb.clearContents()
        pb.setString_forType_(text, NSPasteboardTypeString)
        log.error(
            "Accessibility permission missing — can't paste. "
            "Transcript left on the clipboard: press ⌘V yourself."
        )
        return False
    saved = pb.stringForType_(NSPasteboardTypeString)
    pb.clearContents()
    pb.setString_forType_(text, NSPasteboardTypeString)
    try:
        _press_cmd_v()
        time.sleep(PASTE_SETTLE_SECONDS)
    finally:
        pb.clearContents()
        if saved is not None:
            pb.setString_forType_(saved, NSPasteboardTypeString)
    return True


def _press_cmd_v() -> None:
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for key_down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(source, KEY_V, key_down)
        Quartz.CGEventSetFlags(event, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
