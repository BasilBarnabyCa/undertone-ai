"""Floating "listening" indicator: a non-activating NSPanel overlay.

The menu bar icon is too easy to miss, so while the hotkey is held we show a
small pill near the bottom of the screen carrying Undertone's mark — a
bell-curved cluster of pill-shaped bars, a soundwave frozen mid-pulse. The bars
animate in a staggered ripple so it reads as actively listening.

Brand palette (single cyan-to-blue neon family, restrained — one confident
signal): mint-cyan -> electric cyan -> deep blue, on near-black, with only a
faint close-in glow rather than a heavy bloom.

All AppKit objects must be touched on the main thread; the hotkey callbacks
arrive on the pynput listener thread, so show()/hide() marshal to the main
thread via AppHelper.callAfter when needed.
"""

import warnings

import AppKit
import objc
from PyObjCTools import AppHelper

# CGColor bridging emits a one-time, harmless pointer-ownership warning per call.
warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)

_PILL_WIDTH = 176.0
_PILL_HEIGHT = 46.0
_MARGIN_BOTTOM = 120.0  # px above the bottom edge of the main screen

# Brand palette, mint -> cyan -> deep blue, symmetric across the cluster.
_MINT = (0.549, 1.0, 0.925)   # #8CFFEC
_CYAN = (0.133, 0.910, 1.0)   # #22E8FF
_BLUE = (0.0, 0.706, 1.0)     # #00B4FF

# One (colour, resting-height) per bar — a bell curve, tallest in the middle.
_BARS = [
    (_MINT, 12.0),
    (_CYAN, 22.0),
    (_BLUE, 30.0),
    (_CYAN, 22.0),
    (_MINT, 12.0),
]
_BAR_W = 4.0
_BAR_PITCH = 10.0  # bar width + gap
_CLUSTER_X = 18.0  # left inset of the first bar


def _on_main(fn) -> None:
    if AppKit.NSThread.isMainThread():
        fn()
    else:
        AppHelper.callAfter(fn)


def _cgcolor(rgb: tuple[float, float, float], alpha: float = 1.0):
    return AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
        rgb[0], rgb[1], rgb[2], alpha
    ).CGColor()


class RecordingHUD:
    def __init__(self, text: str = "Listening…") -> None:
        self._panel = None
        self._bars: list = []
        self._text = text

    # -- public API (any thread) --------------------------------------------

    def show(self) -> None:
        _on_main(self._show)

    def hide(self) -> None:
        _on_main(self._hide)

    # -- main-thread implementation -----------------------------------------

    def _build(self) -> None:
        rect = AppKit.NSMakeRect(0, 0, _PILL_WIDTH, _PILL_HEIGHT)
        style = (
            AppKit.NSWindowStyleMaskBorderless
            | AppKit.NSWindowStyleMaskNonactivatingPanel
        )
        panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            rect, style, AppKit.NSBackingStoreBuffered, False
        )
        panel.setLevel_(AppKit.NSStatusWindowLevel)
        panel.setOpaque_(False)
        panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        panel.setHasShadow_(True)
        panel.setIgnoresMouseEvents_(True)
        panel.setReleasedWhenClosed_(False)
        panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
        )

        # The bars + label live on a transparent content view; a Liquid Glass
        # host (macOS 26+) renders the frosted, refracting pill behind them.
        container = AppKit.NSView.alloc().initWithFrame_(rect)
        container.setWantsLayer_(True)
        panel.setContentView_(self._wrap_in_glass(container, rect))

        self._bars = []
        mid_y = _PILL_HEIGHT / 2
        for i, (rgb, height) in enumerate(_BARS):
            x = _CLUSTER_X + i * _BAR_PITCH
            bar = AppKit.NSView.alloc().initWithFrame_(
                AppKit.NSMakeRect(x, mid_y - height / 2, _BAR_W, height)
            )
            bar.setWantsLayer_(True)
            blayer = bar.layer()
            blayer.setCornerRadius_(_BAR_W / 2)
            blayer.setBackgroundColor_(_cgcolor(rgb))
            # Faint, close-in glow — small radius, not a heavy bloom.
            blayer.setShadowColor_(_cgcolor(rgb))
            blayer.setShadowRadius_(2.5)
            blayer.setShadowOpacity_(0.6)
            blayer.setShadowOffset_(AppKit.NSMakeSize(0, 0))
            container.addSubview_(bar)
            self._bars.append(bar)

        label = AppKit.NSTextField.alloc().initWithFrame_(
            AppKit.NSMakeRect(74, (_PILL_HEIGHT - 20) / 2, _PILL_WIDTH - 88, 20)
        )
        label.setStringValue_(self._text)
        label.setBezeled_(False)
        label.setDrawsBackground_(False)
        label.setEditable_(False)
        label.setSelectable_(False)
        label.setTextColor_(AppKit.NSColor.whiteColor())
        label.setFont_(AppKit.NSFont.systemFontOfSize_(14))
        label.cell().setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)
        container.addSubview_(label)

        self._panel = panel

    def _wrap_in_glass(self, content, rect):
        """Host the content in a Liquid Glass pill (macOS 26+), else a dark pill."""
        if hasattr(AppKit, "NSGlassEffectView"):
            glass = AppKit.NSGlassEffectView.alloc().initWithFrame_(rect)
            for setter, value in (
                ("setCornerRadius_", _PILL_HEIGHT / 2),
                # A dark tint keeps the near-black brand look while still getting
                # real Liquid Glass refraction and specular edges.
                (
                    "setTintColor_",
                    AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(
                        0.03, 0.05, 0.08, 0.55
                    ),
                ),
            ):
                if hasattr(glass, setter):
                    getattr(glass, setter)(value)
            glass.setContentView_(content)
            return glass
        # Fallback for < macOS 26: a near-black rounded pill.
        content.layer().setCornerRadius_(_PILL_HEIGHT / 2)
        content.layer().setBackgroundColor_(_cgcolor((0.04, 0.06, 0.09), 0.92))
        return content

    def _position(self) -> None:
        screen = AppKit.NSScreen.mainScreen()
        if screen is None:
            return
        frame = screen.frame()
        x = frame.origin.x + (frame.size.width - _PILL_WIDTH) / 2
        y = frame.origin.y + _MARGIN_BOTTOM
        self._panel.setFrameOrigin_(AppKit.NSMakePoint(x, y))

    def _pulse(self) -> None:
        # Each bar scales vertically on a loop; a per-bar time offset makes the
        # motion ripple across the cluster like a live soundwave.
        for i, bar in enumerate(self._bars):
            anim = AppKit.CABasicAnimation.animationWithKeyPath_("transform.scale.y")
            anim.setFromValue_(1.0)
            anim.setToValue_(0.45)
            anim.setDuration_(0.5)
            anim.setAutoreverses_(True)
            anim.setRepeatCount_(1e9)
            anim.setTimeOffset_(i * 0.12)
            bar.layer().addAnimation_forKey_(anim, "pulse")

    def _show(self) -> None:
        if self._panel is None:
            self._build()
        self._position()
        self._pulse()
        self._panel.orderFrontRegardless()

    def _hide(self) -> None:
        if self._panel is not None:
            self._panel.orderOut_(None)
