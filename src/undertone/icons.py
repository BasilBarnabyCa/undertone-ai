"""Render Undertone's mark as a menu bar icon.

The mark is Basil's monotone soundwave logo (assets/logo_monotone.png):
transparent background, opaque dark fill. Rendered as a macOS *template*
image so the menu bar recolors it automatically for light/dark mode and
selection state — rumps sizes status icons to 20 pt, so we render at 40 px
for retina crispness. Two variants: `active` (full opacity, app running)
and `muted` (dimmed, warming up / busy).
"""

from pathlib import Path

import AppKit

from .config import CONFIG_DIR

_SOURCE_PATH = Path(__file__).with_name("assets") / "logo_monotone.png"
_RENDER_PX = 40  # 2x of the 20 pt menu bar slot

_ACTIVE_PATH = CONFIG_DIR / "menubar_active.png"
_MUTED_PATH = CONFIG_DIR / "menubar_muted.png"


def _render(px: int, alpha: float) -> AppKit.NSImage:
    AppKit.NSApplication.sharedApplication()  # drawing context needs an app
    source = AppKit.NSImage.alloc().initByReferencingFile_(str(_SOURCE_PATH))
    img = AppKit.NSImage.alloc().initWithSize_((px, px))
    img.lockFocus()
    source.drawInRect_fromRect_operation_fraction_(
        AppKit.NSMakeRect(0, 0, px, px),
        AppKit.NSZeroRect,
        AppKit.NSCompositingOperationSourceOver,
        alpha,
    )
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
