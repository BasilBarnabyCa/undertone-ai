"""Render Undertone's mark as a menu bar icon.

The mark is the same bell-curved soundwave cluster the HUD uses, drawn as a
small colored PNG (cyan-to-blue neon family) for the status bar. rumps sizes
status icons to 20 pt, so we render at 40 px for retina crispness. Two variants:
`active` (full color, app running) and `muted` (dimmed, warming up / busy).

Menu bar icons are tiny, so we drop the HUD's glow — it doesn't read at 20 pt —
and keep crisp fills only.
"""

import warnings
from pathlib import Path

import AppKit
import objc

from .config import CONFIG_DIR

warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)

_MINT = (0.549, 1.0, 0.925)   # #8CFFEC
_CYAN = (0.133, 0.910, 1.0)   # #22E8FF
_BLUE = (0.0, 0.706, 1.0)     # #00B4FF

# (colour, resting height) per bar in a 20-unit grid — a bell curve.
_BARS = [
    (_MINT, 7.0),
    (_CYAN, 12.0),
    (_BLUE, 16.0),
    (_CYAN, 12.0),
    (_MINT, 7.0),
]
_BAR_W = 2.4
_PITCH = 3.8
_X0 = 1.2
_GRID = 20.0
_RENDER_PX = 40  # 2x of the 20 pt menu bar slot

_ACTIVE_PATH = CONFIG_DIR / "menubar_active.png"
_MUTED_PATH = CONFIG_DIR / "menubar_muted.png"


def _render(px: int, alpha: float) -> AppKit.NSImage:
    AppKit.NSApplication.sharedApplication()  # drawing context needs an app
    img = AppKit.NSImage.alloc().initWithSize_((px, px))
    img.lockFocus()
    scale = px / _GRID
    for i, (rgb, height) in enumerate(_BARS):
        x = (_X0 + i * _PITCH) * scale
        w = _BAR_W * scale
        bar_h = height * scale
        y = ((_GRID - height) / 2) * scale
        rect = AppKit.NSMakeRect(x, y, w, bar_h)
        path = AppKit.NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(
            rect, w / 2, w / 2
        )
        AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
            rgb[0], rgb[1], rgb[2], alpha
        ).set()
        path.fill()
    img.unlockFocus()
    return img


def _save(img: AppKit.NSImage, path: Path) -> None:
    tiff = img.TIFFRepresentation()
    rep = AppKit.NSBitmapImageRep.imageRepWithData_(tiff)
    png = rep.representationUsingType_properties_(AppKit.NSBitmapImageFileTypePNG, {})
    png.writeToFile_atomically_(str(path), True)


def ensure_icons() -> tuple[str, str]:
    """Render the active/muted menu bar icons to the config dir; return their paths."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    _save(_render(_RENDER_PX, 1.0), _ACTIVE_PATH)
    _save(_render(_RENDER_PX, 0.35), _MUTED_PATH)
    return str(_ACTIVE_PATH), str(_MUTED_PATH)
