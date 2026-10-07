"""Design tokens + helpers.

Every colour / radius below is copied from the original web stylesheet
(static/style.css) so the native app keeps exactly the same look.
"""
from __future__ import annotations

import sys
import tkinter as tk
import tkinter.font as tkfont
from functools import lru_cache
from pathlib import Path

import customtkinter as ctk
import numpy as np
from customtkinter.windows.widgets.scaling.scaling_tracker import ScalingTracker
from PIL import Image

if getattr(sys, "frozen", False):
    exe_dir = Path(sys.executable).parent
    meipass = Path(getattr(sys, "_MEIPASS", exe_dir))
    candidates = [
        exe_dir / "_internal" / "assets",
        meipass / "_internal" / "assets",
        exe_dir / "assets",
        meipass / "assets",
    ]
    ASSETS = next((c for c in candidates if (c / "emoji").exists()), next((c for c in candidates if c.exists()), exe_dir / "assets"))
    ROOT_DIR = exe_dir
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    ASSETS = (ROOT_DIR / "assets") if (ROOT_DIR / "assets").exists() else (ROOT_DIR.parent / "assets")

# --------------------------------------------------------------------------
# Colour palette (from :root in style.css)
# --------------------------------------------------------------------------
WIN_BG = "#090d16"          # --win-titlebar-bg  (title bar, status bar)
SIDEBAR_BG = "#0d1322"
SIDEBAR_BORDER = "#1a233a"
SIDEBAR_TEXT = "#94a3b8"
SIDEBAR_TEXT_HOVER = "#f1f5f9"
SIDEBAR_ACTIVE_BG = "#1e293b"

CANVAS_BG = "#f8fafc"
PANEL = "#ffffff"
BORDER = "#e2e8f0"
BORDER_SUBTLE = "#edf2f7"

TEXT = "#0f172a"
TEXT2 = "#475569"
MUTED = "#64748b"
LIGHT = "#94a3b8"

RED = "#ea2839"
RED_HOVER = "#cf1b2c"
RED_SIDEBAR_HOVER = "#d41e2e"
BLUE = "#3b82f6"
GREEN = "#10b981"
AMBER = "#f59e0b"
VIOLET = "#8b5cf6"
CYAN = "#06b6d4"
ORANGE = "#f97316"
SLATE = "#64748b"

BADGE_PASS_BG, BADGE_PASS_TEXT = "#dcfce7", "#15803d"
BADGE_FAIL_BG, BADGE_FAIL_TEXT = "#fee2e2", "#b91c1c"

R_SM, R_MD, R_LG, R_XL = 6, 10, 14, 20


def blend(fg: str, alpha: float, bg: str) -> str:
    """Colour of *fg* drawn at *alpha* opacity over *bg* (replaces CSS rgba())."""
    f = [int(fg[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(bg[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3))


# --------------------------------------------------------------------------
# Fonts: Poppins (brand), Inter (UI), JetBrains Mono (register numbers)
# The TTFs ship in assets/fonts and are registered privately for this process.
# --------------------------------------------------------------------------
def register_fonts() -> None:
    fonts_dir = ASSETS / "fonts"
    if sys.platform.startswith("win"):
        import ctypes
        FR_PRIVATE = 0x10
        for ttf in fonts_dir.glob("*.ttf"):
            try:
                ctypes.windll.gdi32.AddFontResourceExW(str(ttf), FR_PRIVATE, 0)
            except Exception:
                pass
    # matplotlib (charts) can load the same files on any platform
    try:
        from matplotlib import font_manager
        for ttf in fonts_dir.glob("Inter-*.ttf"):
            font_manager.fontManager.addfont(str(ttf))
    except Exception:
        pass


# role -> candidate (family, bold) pairs, best match first
_ROLES = {
    "brand":  [("Poppins ExtraBold", False), ("Poppins", True)],           # 800
    "brand7": [("Poppins", True)],                                          # 700
    "ui":     [("Inter", False)],
    "ui5":    [("Inter Medium", False), ("Inter", False)],
    "ui6":    [("Inter SemiBold", False), ("Inter", True)],
    "ui7":    [("Inter", True)],
    "mono":   [("JetBrains Mono", False)],
    "mono6":  [("JetBrains Mono SemiBold", False), ("JetBrains Mono", True)],
    "mono7":  [("JetBrains Mono", True)],
}
_available: set[str] | None = None


def _resolve(role: str) -> tuple[str, bool]:
    global _available
    if _available is None:
        _available = {f.lower() for f in tkfont.families()}
    for family, bold in _ROLES[role]:
        if family.lower() in _available:
            return family, bold
    if role.startswith("mono"):
        return "Consolas", role != "mono"
    return "Segoe UI", role not in ("ui", "ui5")


@lru_cache(maxsize=None)
def F(role: str = "ui", size: int = 13) -> ctk.CTkFont:
    """CTkFont for a role. *size* is in CSS pixels (CTk scales it for the display)."""
    family, bold = _resolve(role)
    return ctk.CTkFont(family=family, size=size, weight="bold" if bold else "normal")


_tkfonts: dict = {}


def TkF(role: str, size: float, scale: float) -> tkfont.Font:
    """Raw Tk font for canvas drawing (already multiplied by the DPI scale)."""
    key = (role, size, round(scale, 3))
    if key not in _tkfonts:
        family, bold = _resolve(role)
        _tkfonts[key] = tkfont.Font(family=family, size=-max(1, round(size * scale)),
                                    weight="bold" if bold else "normal")
    return _tkfonts[key]


def scale_of(widget) -> float:
    try:
        return float(ScalingTracker.get_widget_scaling(widget))
    except Exception:
        return 1.0


def ellipsize(text: str, font: tkfont.Font, max_px: float) -> str:
    text = str(text)
    if font.measure(text) <= max_px:
        return text
    while text and font.measure(text + "…") > max_px:
        text = text[:-1]
    return text + "…"


# --------------------------------------------------------------------------
# Images
# --------------------------------------------------------------------------
@lru_cache(maxsize=None)
def _pil(path: str) -> Image.Image:
    return Image.open(path).convert("RGBA")


def _ctkimg(path: str, w: int, h: int) -> ctk.CTkImage:
    im = _pil(path)
    return ctk.CTkImage(light_image=im, dark_image=im, size=(w, h))


@lru_cache(maxsize=None)
def _logo_pil() -> Image.Image:
    """logo.png has opaque black corners; the web UI hid them with border-radius (~19 %)."""
    from PIL import ImageDraw
    im = _pil(str(ASSETS / "logo.png")).copy()
    n = im.width
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, n - 1, n - 1), radius=int(n * 0.19), fill=255)
    im.putalpha(mask)
    return im.resize((256, 256), Image.LANCZOS)


def logo(size: int, rounded: bool = True) -> ctk.CTkImage:
    im = _logo_pil() if rounded else _pil(str(ASSETS / "logo.png")).resize((256, 256), Image.LANCZOS)
    return ctk.CTkImage(light_image=im, dark_image=im, size=(size, size))


def emoji(name: str, size: int) -> ctk.CTkImage:
    return _ctkimg(str(ASSETS / "emoji" / f"{name}.png"), size, size)


def icon(name: str, size: int) -> ctk.CTkImage:
    return _ctkimg(str(ASSETS / "icons" / f"{name}.png"), size, size)


def pil_icon(name: str, folder: str = "icons") -> Image.Image:
    return _pil(str(ASSETS / folder / f"{name}.png"))


# --------------------------------------------------------------------------
# Gradients (replace CSS linear-gradient / radial-gradient)
# --------------------------------------------------------------------------
def _hex(c: str) -> np.ndarray:
    return np.array([int(c[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.float32)


def linear_gradient(w: int, h: int, c1: str, c2: str, angle: float = 135.0) -> Image.Image:
    """CSS-accurate linear-gradient(<angle>deg, c1, c2)."""
    w, h = max(2, int(w)), max(2, int(h))
    th = np.radians(angle)
    dx, dy = np.sin(th), -np.cos(th)
    length = abs(w * dx) + abs(h * dy)
    xs, ys = np.meshgrid(np.arange(w) - w / 2 + .5, np.arange(h) - h / 2 + .5)
    t = np.clip((xs * dx + ys * dy) / length + .5, 0, 1)[..., None]
    arr = _hex(c1) * (1 - t) + _hex(c2) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def radial_gradient(w: int, h: int, c1: str, c2: str, cx: float = .5, cy: float = .15) -> Image.Image:
    """radial-gradient(circle at cx cy, c1 0%, c2 100%) - farthest-corner sized."""
    w, h = max(2, int(w)), max(2, int(h))
    px, py = cx * w, cy * h
    radius = max(np.hypot(px - x, py - y) for x in (0, w) for y in (0, h))
    xs, ys = np.meshgrid(np.arange(w) + .5, np.arange(h) + .5)
    t = np.clip(np.hypot(xs - px, ys - py) / radius, 0, 1)[..., None]
    arr = _hex(c1) * (1 - t) + _hex(c2) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB")


# --------------------------------------------------------------------------
# Native Windows chrome: dark title bar in the app colour
# --------------------------------------------------------------------------
def _colorref(hex_color: str) -> int:
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return (b << 16) | (g << 8) | r


def style_titlebar(window, caption: str = WIN_BG, text: str = "#ffffff") -> None:
    """Colour the real Windows title bar like the original custom title bar.
    Harmless no-op on Windows 10 / other platforms."""
    if not sys.platform.startswith("win"):
        return

    def apply():
        try:
            import ctypes
            from ctypes import wintypes
            hwnd = ctypes.windll.user32.GetParent(window.winfo_id()) or window.winfo_id()
            dwm = ctypes.windll.dwmapi

            def setattr_(attr, value):
                v = ctypes.c_int(value)
                return dwm.DwmSetWindowAttribute(wintypes.HWND(hwnd), attr, ctypes.byref(v), ctypes.sizeof(v))

            if setattr_(20, 1) != 0:        # dark mode (Win10 20H1+/Win11)
                setattr_(19, 1)
            setattr_(35, _colorref(caption))    # caption colour  (Win11)
            setattr_(36, _colorref(text))       # caption text    (Win11)
            setattr_(34, _colorref(caption))    # border colour   (Win11)
        except Exception:
            pass

    window.after(60, apply)
    window.after(350, apply)    # CTk re-applies its own chrome shortly after start-up


def set_window_icon(window) -> None:
    ico = ASSETS / "logo.ico"
    png = ASSETS / "logo.png"

    def apply():
        try:
            if sys.platform.startswith("win") and ico.exists():
                window.iconbitmap(str(ico))
            else:
                from PIL import ImageTk
                window._icon_ref = ImageTk.PhotoImage(_pil(str(png)).resize((64, 64)))
                window.iconphoto(True, window._icon_ref)
        except Exception:
            pass

    apply()
    window.after(250, apply)    # CTkToplevel installs its default icon after ~200 ms


def rounded_points(x1, y1, x2, y2, r, steps: int = 8) -> list[float]:
    """Perimeter of a rounded rectangle as a flat polygon point list."""
    import math
    pts: list[float] = []
    corners = [(x2 - r, y1 + r, -90), (x2 - r, y2 - r, 0), (x1 + r, y2 - r, 90), (x1 + r, y1 + r, 180)]
    for cx, cy, start in corners:
        for i in range(steps + 1):
            a = math.radians(start + 90 * i / steps)
            pts += [cx + r * math.cos(a), cy + r * math.sin(a)]
    return pts


def round_rect(canvas: tk.Canvas, x1, y1, x2, y2, r, **kw):
    return canvas.create_polygon(rounded_points(x1, y1, x2, y2, r), **kw)
