"""Deliver text into the frontmost app: clipboard swap + simulated Cmd+V.

Pasting is far more reliable than synthetic per-character typing (IME apps,
Electron, and terminals all handle it), and it's what Wispr Flow does too.
The user's clipboard is restored afterwards no matter what.
"""

import logging
import time

import Quartz
from AppKit import NSPasteboard, NSPasteboardTypeString

log = logging.getLogger(__name__)

KEY_V = 9  # kVK_ANSI_V
# How long the target app gets to read the pasteboard before we restore it.
PASTE_SETTLE_SECONDS = 0.25


def paste_text(text: str) -> None:
    pb = NSPasteboard.generalPasteboard()
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


def _press_cmd_v() -> None:
    source = Quartz.CGEventSourceCreate(Quartz.kCGEventSourceStateHIDSystemState)
    for key_down in (True, False):
        event = Quartz.CGEventCreateKeyboardEvent(source, KEY_V, key_down)
        Quartz.CGEventSetFlags(event, Quartz.kCGEventFlagMaskCommand)
        Quartz.CGEventPost(Quartz.kCGHIDEventTap, event)
