"""Reusable widgets that reproduce the pieces of the original web UI."""
from __future__ import annotations

import bisect
import sys
import tkinter as tk
from typing import Callable, Sequence

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from . import theme as T
from .theme import F, TkF, scale_of

# --------------------------------------------------------------------------
# Basic containers
# --------------------------------------------------------------------------


class Pane(ctk.CTkScrollableFrame):
    """One scrolling content pane (.desktop-pane inside .desktop-viewport)."""

    def __init__(self, master):
        super().__init__(master, fg_color=T.CANVAS_BG, corner_radius=0,
                         scrollbar_button_color="#cbd5e1", scrollbar_button_hover_color="#94a3b8")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=24, pady=24)
        # CTk's default wheel step is far too large for a long page
        try:
            self._parent_canvas.configure(yscrollincrement=16)
        except Exception:
            pass

    def _mouse_wheel_all(self, event):
        # Suppress CTk's buggy global listener; scrolling is handled reliably by AppShell
        pass


def Card(master, **kw) -> ctk.CTkFrame:
    """.desktop-card"""
    opts = dict(fg_color=T.PANEL, border_width=1, border_color=T.BORDER, corner_radius=T.R_LG)
    opts.update(kw)
    return ctk.CTkFrame(master, **opts)


def rich(master, parts: Sequence[tuple], bg="transparent", **pack) -> ctk.CTkFrame:
    """A row of differently styled labels, e.g. [("Passed: ", "ui", 12, color), ("94", "ui7", 12, color)]."""
    row = ctk.CTkFrame(master, fg_color=bg)
    for text, role, size, color in parts:
        ctk.CTkLabel(row, text=text, font=F(role, size), text_color=color, fg_color="transparent",
                     padx=0, pady=0).pack(side="left")
    return row


def card_head(master, title: str, hint: str | None = None, hint_color=T.MUTED, hint_size=11) -> ctk.CTkFrame:
    head = ctk.CTkFrame(master, fg_color="transparent")
    ctk.CTkLabel(head, text=title, font=F("ui7", 14), text_color=T.TEXT, anchor="w").pack(side="left")
    if hint:
        ctk.CTkLabel(head, text=hint, font=F("ui", hint_size), text_color=hint_color).pack(side="right")
    return head


def section_intro(master, title: str, sub: str, center: bool = False) -> ctk.CTkFrame:
    f = ctk.CTkFrame(master, fg_color="transparent")
    anchor = "center" if center else "w"
    ctk.CTkLabel(f, text=title, font=F("ui7", 18), text_color=T.TEXT, anchor=anchor).pack(fill="x")
    ctk.CTkLabel(f, text=sub, font=F("ui", 13), text_color=T.MUTED, anchor=anchor).pack(fill="x", pady=(4, 0))
    return f


def Pill(master, text: str, bg: str, fg: str, role="ui7", size=11, padx=8, pady=3, radius=12,
         outer_bg="transparent") -> ctk.CTkFrame:
    f = ctk.CTkFrame(master, fg_color=bg, corner_radius=radius, bg_color=outer_bg)
    ctk.CTkLabel(f, text=text, font=F(role, size), text_color=fg, fg_color="transparent").pack(padx=padx, pady=pady)
    return f


# --------------------------------------------------------------------------
# Buttons (.desktop-btn-*, .sidebar-btn-*, .pag-btn)
# --------------------------------------------------------------------------
_BTN = {
    "primary": dict(fg_color=T.RED, hover_color=T.RED_HOVER, text_color="#ffffff", border_width=0),
    "accent": dict(fg_color=T.TEXT, hover_color=T.SIDEBAR_ACTIVE_BG, text_color="#ffffff", border_width=0),
    "outline": dict(fg_color="#ffffff", hover_color="#f8fafc", text_color=T.TEXT, border_width=1, border_color=T.BORDER),
    "sb_outline": dict(fg_color=T.blend("#ffffff", .05, T.SIDEBAR_BG), hover_color=T.blend("#ffffff", .10, T.SIDEBAR_BG),
                       text_color="#cbd5e1", border_width=1, border_color=T.blend("#ffffff", .10, T.SIDEBAR_BG)),
    "sb_primary": dict(fg_color=T.RED, hover_color=T.RED_SIDEBAR_HOVER, text_color="#ffffff", border_width=0),
    "pag": dict(fg_color="#f1f5f9", hover_color="#e2e8f0", text_color=T.TEXT, border_width=1, border_color=T.BORDER),
}


def AppButton(master, text: str, kind: str = "primary", command=None, image=None, compound="left",
              height=34, size=12, radius=T.R_MD, width=0, **kw) -> ctk.CTkButton:
    opts = dict(_BTN[kind])
    opts.update(kw)
    if not width:                                   # fit the text (+ icon + 14px padding each side)
        try:
            font = TkF("ui6", size, 1.0)
            iw = (image.cget("size")[0] + 8) if image is not None else 0
            width = int(font.measure(text) + iw + 28 + (2 if opts.get("border_width") else 0))
        except Exception:
            width = 0
    btn = ctk.CTkButton(master, text=text, command=command, image=image, compound=compound, height=height,
                        width=width, corner_radius=radius, font=F("ui6", size), cursor="hand2", **opts)
    return btn


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------
class SearchBox(ctk.CTkFrame):
    """.search-box : icon + text input, border turns red on focus."""

    def __init__(self, master, placeholder: str, command: Callable[[], None]):
        super().__init__(master, fg_color="#ffffff", border_width=1, border_color=T.BORDER,
                         corner_radius=T.R_MD, height=38)
        self.pack_propagate(False)
        ctk.CTkLabel(self, text="", image=T.icon("search_muted", 16), width=16, fg_color="transparent"
                     ).pack(side="left", padx=(12, 0))
        self.entry = ctk.CTkEntry(self, placeholder_text=placeholder, border_width=0,
                                  fg_color="#ffffff", text_color=T.TEXT, placeholder_text_color="#94a3b8",
                                  font=F("ui", 13), height=34, corner_radius=0)
        self.entry.pack(side="left", fill="both", expand=True, padx=(4, 8), pady=1)
        self._command = command
        self._last = ""
        # (a textvariable would disable CTk's placeholder, so listen to key events instead)
        self.entry.bind("<KeyRelease>", self._typed, add="+")
        self.entry.bind("<FocusIn>", lambda e: self.configure(border_color=T.RED), add="+")
        self.entry.bind("<FocusOut>", lambda e: self.configure(border_color=T.BORDER), add="+")

    def _typed(self, _e=None):
        value = self.entry.get()
        if value != self._last:
            self._last = value
            self._command()

    def get(self) -> str:
        return self.entry.get()


class Select(ctk.CTkFrame):
    """.desktop-select : bordered drop-down; the whole box opens the list."""

    def __init__(self, master, values: list[str], command: Callable[[], None] | None = None, width=170,
                 height=36, size=12):
        super().__init__(master, fg_color="#ffffff", border_width=1, border_color=T.BORDER,
                         corner_radius=T.R_MD, height=height, width=width)
        self.pack_propagate(False)
        self._values = list(values)
        self._command = command
        self.menu = ctk.CTkOptionMenu(
            self, values=self._values, command=self._changed, fg_color="#ffffff", button_color="#ffffff",
            button_hover_color="#f1f5f9", text_color=T.TEXT, dropdown_fg_color="#ffffff",
            dropdown_hover_color="#f1f5f9", dropdown_text_color=T.TEXT, font=F("ui", size),
            dropdown_font=F("ui", size), corner_radius=T.R_MD - 2, anchor="w", dynamic_resizing=False,
            height=height - 4, width=width - 4)
        self.menu.pack(padx=1, pady=1, fill="both", expand=True)

    def _changed(self, _value):
        if self._command:
            self._command()

    def get(self) -> str:
        return self.menu.get()

    def index(self) -> int:
        try:
            return self._values.index(self.menu.get())
        except ValueError:
            return 0

    def set_values(self, values: list[str], select: int = 0):
        self._values = list(values)
        self.menu.configure(values=self._values)
        self.menu.set(self._values[select] if self._values else "")


class Pagination(ctk.CTkFrame):
    """.desktop-pagination"""

    def __init__(self, master, on_prev, on_next):
        super().__init__(master, fg_color="transparent")
        self.prev = AppButton(self, "←  Previous", "pag", on_prev, height=30, radius=T.R_SM)
        self.label = ctk.CTkLabel(self, text="Page 1 of 1", font=F("ui", 12), text_color=T.MUTED)
        self.next = AppButton(self, "Next  →", "pag", on_next, height=30, radius=T.R_SM)
        self.next.pack(side="right")
        self.label.pack(side="right", padx=12)
        self.prev.pack(side="right")

    def set_label(self, text: str):
        self.label.configure(text=text)


# --------------------------------------------------------------------------
# Table cell descriptors
# --------------------------------------------------------------------------
class Txt:
    def __init__(self, text, role="ui", size=13, color=T.TEXT):
        self.text, self.role, self.size, self.color = ("-" if text is None else str(text)), role, size, color


class Inline:
    """Several styled text runs on one line, e.g. **668** / 700"""

    def __init__(self, *parts: Txt, gap: float = 4):
        self.parts, self.gap = parts, gap


class TwoLine:
    def __init__(self, top: Txt, bottom: Txt):
        self.top, self.bottom = top, bottom


class BadgeCell:
    """.badge.pass / .badge.fail (anything else renders as plain bold text, as in the original CSS)."""

    def __init__(self, text, kind="plain"):
        self.text, self.kind = str(text), kind


class CountCell:
    """.badge-count-red"""

    def __init__(self, text):
        self.text = str(text)


class WrapCell:
    def __init__(self, text, role="ui", size=12, color=T.TEXT2):
        self.text, self.role, self.size, self.color = str(text), role, size, color


def wrap_lines(text: str, font, max_px: float) -> list[str]:
    words, lines, cur = text.split(" "), [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.measure(trial) <= max_px or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


# --------------------------------------------------------------------------
# DataTable: canvas-drawn table (.desktop-table inside .desktop-table-container)
# --------------------------------------------------------------------------
class DataTable(tk.Canvas):
    HEAD_BG = "#f8fafc"
    HOVER_BG = "#f1f5f9"

    def __init__(self, master, columns: list[dict], *, max_height=520, row_h=42, head_h=38,
                 on_click: Callable[[int], None] | None = None, empty_text="No records found.",
                 outer_bg=T.PANEL, radius=T.R_MD, pad_x=14):
        super().__init__(master, bg=T.PANEL, highlightthickness=0, bd=0, height=int(head_h + row_h))
        self.cols, self.max_h, self.row_h, self.head_h = columns, max_height, row_h, head_h
        self.on_click, self.empty_text, self.outer_bg, self.radius, self.pad_x = on_click, empty_text, outer_bg, radius, pad_x
        self._rows: list[list] = []
        self._offsets: list[float] = []
        self._heights: list[float] = []
        self._content_h = 0.0
        self._scroll = 0.0
        self._hover = -1
        self._bg_ids: dict[int, int] = {}
        self._thumb: tuple[float, float] | None = None
        self._drag: tuple[float, float] | None = None
        self._size = (0, 0)
        self._col_x: list[float] = []
        self._col_w: list[float] = []
        self._need = None
        self._floor: list[float] = []
        self.bind("<Configure>", self._on_configure)
        self.bind("<Motion>", self._on_motion)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_press)
        self.bind("<B1-Motion>", self._on_drag)
        self.bind("<ButtonRelease-1>", lambda e: setattr(self, "_drag", None))
        self.bind("<MouseWheel>", self._on_wheel)
        self.bind("<Button-4>", lambda e: self._on_wheel(e, 1))
        self.bind("<Button-5>", lambda e: self._on_wheel(e, -1))

    # ---- public ---------------------------------------------------------
    def set_rows(self, rows: list[list]):
        self._rows = rows
        self._need = None
        self._scroll = 0.0
        self._hover = -1
        if self.winfo_width() > 10:
            self._relayout()
            self._redraw()

    def set_columns(self, columns: list[dict]):
        self.cols = columns
        self._need = None
        self._scroll = 0.0
        self._hover = -1
        if self.winfo_width() > 10:
            self._relayout()
            self._redraw()

    # ---- layout ---------------------------------------------------------
    @property
    def S(self) -> float:
        return scale_of(self)

    def _natural(self, cell, S) -> float:
        """Natural (unwrapped) pixel width of a cell's content - what a browser's auto table layout uses."""
        if cell is None or isinstance(cell, str):
            return TkF("ui", 13, S).measure("-" if cell is None else cell)
        if isinstance(cell, Txt):
            return TkF(cell.role, cell.size, S).measure(cell.text)
        if isinstance(cell, Inline):
            return sum(TkF(p.role, p.size, S).measure(p.text) for p in cell.parts) + cell.gap * S * (len(cell.parts) - 1)
        if isinstance(cell, TwoLine):
            return max(self._natural(cell.top, S), self._natural(cell.bottom, S))
        if isinstance(cell, (BadgeCell, CountCell)):
            f = TkF("ui7", 12 if isinstance(cell, CountCell) else 11, S)
            return f.measure(cell.text.upper() if isinstance(cell, BadgeCell) else cell.text) + 16 * S
        if isinstance(cell, WrapCell):
            f = TkF(cell.role, cell.size, S)
            return max((f.measure(w) for w in cell.text.split()), default=0)
        return 0

    def _relayout(self):
        S = self.S
        W = self.winfo_width() / S
        n = len(self.cols)
        pad2 = 2 * self.pad_x
        if self._need is None:
            hf = TkF("ui7", 11, S)
            self._floor = [hf.measure(c["title"].upper()) / S + pad2 for c in self.cols]
            need = [0.0] * n
            for row in self._rows:
                for ci, cell in enumerate(row[:n]):
                    need[ci] = max(need[ci], self._natural(cell, S) / S + pad2)
            self._need = need
        flex = [c.get("flex", 1) for c in self.cols]
        pref = [max(c.get("w", 0), self._need[i], self._floor[i]) for i, c in enumerate(self.cols)]
        lo = [self._floor[i] if flex[i] > 0 else pref[i] for i in range(n)]
        total = sum(pref)
        if total <= W:
            extra, tf = W - total, (sum(flex) or 1)
            widths = [pref[i] + extra * flex[i] / tf for i in range(n)]
        else:
            deficit = total - W
            room = sum(pref[i] - lo[i] for i in range(n))
            if room >= deficit:
                widths = [pref[i] - deficit * (pref[i] - lo[i]) / room for i in range(n)]
            else:                                    # still too wide: shrink every column evenly
                widths = [l * W / sum(lo) for l in lo]
        self._col_w = widths
        self._col_x, x = [], 0.0
        for w in self._col_w:
            self._col_x.append(x)
            x += w
        self._heights, self._offsets, y = [], [], 0.0
        for row in self._rows:
            h = self.row_h
            for ci, cell in enumerate(row):
                if isinstance(cell, WrapCell):
                    font = TkF(cell.role, cell.size, S)
                    n = len(wrap_lines(cell.text, font, (self._col_w[ci] - 2 * self.pad_x) * S))
                    h = max(h, 24 + n * cell.size * 1.25 + 6)
                elif isinstance(cell, TwoLine):
                    h = max(h, 52)
            self._offsets.append(y)
            self._heights.append(h)
            y += h
        if not self._rows:
            self._heights, self._offsets, y = [66.0], [0.0], 66.0
        self._content_h = y
        want = min(self.head_h + self._content_h, self.max_h)
        target_h = int(round(want * S))
        if abs(self.winfo_height() - target_h) > 2:
            self.configure(height=target_h)
        self._scroll = min(self._scroll, self._max_scroll(want))

    def _max_scroll(self, view_total: float | None = None) -> float:
        if view_total is None:
            view_total = self.winfo_height() / self.S
        return max(0.0, self._content_h - (view_total - self.head_h))

    def _on_configure(self, e):
        if (e.width, e.height) == self._size or e.width < 10:
            return
        w_changed = e.width != self._size[0]
        self._size = (e.width, e.height)
        if w_changed or not self._col_w:
            self._relayout()
        self._redraw()

    # ---- drawing --------------------------------------------------------
    def _redraw(self):
        self.delete("all")
        self._bg_ids = {}
        S = self.S
        W, H = self.winfo_width(), self.winfo_height()
        top = self.head_h * S
        if not self._rows:
            self.create_text(W / 2, top + 33 * S, text=self.empty_text, fill=T.MUTED, font=TkF("ui", 13, S))
        else:
            first = max(0, bisect.bisect_right(self._offsets, self._scroll) - 1)
            for i in range(first, len(self._rows)):
                ry = top + (self._offsets[i] - self._scroll) * S
                if ry > H:
                    break
                self._draw_row(i, ry, S, W)
        # sticky header (drawn after the rows so it covers them)
        self.create_rectangle(0, 0, W, top, fill=self.HEAD_BG, width=0)
        hf = TkF("ui7", 11, S)
        for c, x, w in zip(self.cols, self._col_x, self._col_w):
            self.create_text((x + self.pad_x) * S, top / 2, anchor="w", fill=T.MUTED, font=hf,
                             text=T.ellipsize(c["title"].upper(), hf, (w - 2 * self.pad_x) * S))
        self.create_line(0, top - 1, W, top - 1, fill=T.BORDER)
        self._draw_scrollbar(S, W, H, top)
        self._draw_frame(S, W, H)

    def _draw_row(self, i, ry, S, W):
        rh = self._heights[i] * S
        bg = self.create_rectangle(0, ry, W, ry + rh, fill=self.HOVER_BG if i == self._hover else T.PANEL, width=0)
        self._bg_ids[i] = bg
        self.create_line(0, ry + rh - 1, W, ry + rh - 1, fill=T.BORDER_SUBTLE)
        row = self._rows[i]
        ymid = ry + rh / 2
        for ci, cell in enumerate(row):
            x = (self._col_x[ci] + self.pad_x) * S
            maxw = (self._col_w[ci] - 2 * self.pad_x) * S
            self._draw_cell(cell, x, ymid, maxw, S, ry)

    def _text(self, x, y, t: Txt, maxw, S, anchor="w"):
        font = TkF(t.role, t.size, S)
        txt = T.ellipsize(t.text, font, maxw)
        self.create_text(x, y, text=txt, anchor=anchor, fill=t.color, font=font)
        return font.measure(txt)

    def _draw_cell(self, cell, x, ymid, maxw, S, ry):
        if isinstance(cell, str) or cell is None:
            self._text(x, ymid, Txt(cell), maxw, S)
        elif isinstance(cell, Txt):
            self._text(x, ymid, cell, maxw, S)
        elif isinstance(cell, Inline):
            cx = x
            for part in cell.parts:
                cx += self._text(cx, ymid, part, max(10, maxw - (cx - x)), S) + cell.gap * S
        elif isinstance(cell, TwoLine):
            self._text(x, ymid - 8 * S, cell.top, maxw, S)
            self._text(x, ymid + 9 * S, cell.bottom, maxw, S)
        elif isinstance(cell, BadgeCell):
            self._badge(x, ymid, cell, S)
        elif isinstance(cell, CountCell):
            font = TkF("ui7", 12, S)
            tw = font.measure(cell.text)
            T.round_rect(self, x, ymid - 10 * S, x + tw + 16 * S, ymid + 10 * S, 8 * S, fill=T.BADGE_FAIL_BG, outline="")
            self.create_text(x + 8 * S, ymid, text=cell.text, anchor="w", fill=T.BADGE_FAIL_TEXT, font=font)
        elif isinstance(cell, WrapCell):
            font = TkF(cell.role, cell.size, S)
            lines = wrap_lines(cell.text, font, maxw)
            lh = cell.size * 1.25 * S
            y0 = ymid - lh * len(lines) / 2 + lh / 2
            for k, line in enumerate(lines):
                self.create_text(x, y0 + k * lh, text=line, anchor="w", fill=cell.color, font=font)

    def _badge(self, x, ymid, cell: BadgeCell, S):
        font = TkF("ui7", 11, S)
        text = cell.text.upper()
        if cell.kind in ("pass", "fail"):
            bg, fg = (T.BADGE_PASS_BG, T.BADGE_PASS_TEXT) if cell.kind == "pass" else (T.BADGE_FAIL_BG, T.BADGE_FAIL_TEXT)
            tw = font.measure(text)
            T.round_rect(self, x, ymid - 10 * S, x + tw + 16 * S, ymid + 10 * S, 10 * S, fill=bg, outline="")
            self.create_text(x + 8 * S, ymid, text=text, anchor="w", fill=fg, font=font)
        else:   # e.g. ABSENT: the original stylesheet defines no colours for it
            self.create_text(x + 8 * S, ymid, text=text, anchor="w", fill=T.TEXT, font=font)

    def _draw_scrollbar(self, S, W, H, top):
        self._thumb = None
        ms = self._max_scroll()
        if ms <= 0:
            return
        track = H - top - 8 * S
        body = H / S - self.head_h
        th = max(28 * S, track * body / self._content_h)
        ty = top + 4 * S + (track - th) * (self._scroll / ms)
        x2 = W - 4 * S
        T.round_rect(self, x2 - 6 * S, ty, x2, ty + th, 3 * S, fill="#cbd5e1", outline="")
        self._thumb = (ty, ty + th)

    def _draw_frame(self, S, W, H):
        r = self.radius * S
        corners = [(0, 0, 1, 1), (W, 0, -1, 1), (W, H, -1, -1), (0, H, 1, -1)]
        import math
        for cx, cy, sx, sy in corners:
            pts = [cx, cy]
            for k in range(9):
                a = math.radians(90 * k / 8)
                pts += [cx + sx * (r - r * math.sin(a)), cy + sy * (r - r * math.cos(a))]
            self.create_polygon(pts, fill=self.outer_bg, outline="")
        bw = max(1, round(S))
        self.create_polygon(T.rounded_points(bw / 2, bw / 2, W - bw / 2, H - bw / 2, r), fill="",
                            outline=T.BORDER_SUBTLE, width=bw)

    # ---- interaction ----------------------------------------------------
    def _row_at(self, y_px) -> int:
        S = self.S
        if y_px < self.head_h * S or not self._rows:
            return -1
        pos = y_px / S - self.head_h + self._scroll
        i = bisect.bisect_right(self._offsets, pos) - 1
        return i if 0 <= i < len(self._rows) and pos <= self._content_h else -1

    def _on_motion(self, e):
        i = self._row_at(e.y)
        if i != self._hover:
            if self._hover in self._bg_ids:
                self.itemconfigure(self._bg_ids[self._hover], fill=T.PANEL)
            if i in self._bg_ids:
                self.itemconfigure(self._bg_ids[i], fill=self.HOVER_BG)
            self._hover = i
        self.configure(cursor="hand2" if (i >= 0 and self.on_click) else "")

    def _on_leave(self, _e):
        if self._hover in self._bg_ids:
            self.itemconfigure(self._bg_ids[self._hover], fill=T.PANEL)
        self._hover = -1

    def _on_press(self, e):
        S = self.S
        if self._thumb and e.x >= self.winfo_width() - 16 * S and self._thumb[0] <= e.y <= self._thumb[1]:
            self._drag = (e.y, self._scroll)
            return
        i = self._row_at(e.y)
        if i >= 0 and self.on_click:
            self.on_click(i)

    def _on_drag(self, e):
        if not self._drag:
            return
        S = self.S
        track = self.winfo_height() - self.head_h * S - 8 * S
        ms = self._max_scroll()
        body = self.winfo_height() / S - self.head_h
        th = max(28 * S, track * body / self._content_h)
        ratio = (e.y - self._drag[0]) / max(1.0, track - th)
        self._scroll = min(ms, max(0.0, self._drag[1] + ratio * ms))
        self._redraw()

    def _on_wheel(self, e, direction=None):
        ms = self._max_scroll()
        if ms <= 0:
            return None             # nothing to scroll here -> let the page scroll
        if direction is None:
            step = -(e.delta / 120.0) * 42
        else:
            step = -direction * 42
        new_scroll = min(ms, max(0.0, self._scroll + step))
        if new_scroll == self._scroll:
            return None             # at table boundary -> let the page scroll!
        self._scroll = new_scroll
        self._redraw()
        return "break"


# --------------------------------------------------------------------------
# GradientCanvas: dark gradient panels (banner / export hero)
# --------------------------------------------------------------------------
class GradientCanvas(tk.Canvas):
    def __init__(self, master, c1: str, c2: str, height: int, layout: Callable[["GradientCanvas"], None],
                 radius: int = T.R_LG, outer_bg: str = T.CANVAS_BG, angle: float = 135):
        S = scale_of(master)
        super().__init__(master, highlightthickness=0, bd=0, bg=outer_bg, height=int(height * S))
        self.c1, self.c2, self.radius, self.outer_bg, self.angle = c1, c2, radius, outer_bg, angle
        self.layout = layout
        self._photo = None
        self._size = (0, 0)
        self._job = None
        self.bind("<Configure>", self._on_configure)

    @property
    def S(self) -> float:
        return scale_of(self)

    def _on_configure(self, e):
        if (e.width, e.height) == self._size or e.width < 10 or e.height < 10:
            return
        self._size = (e.width, e.height)
        if self._job:
            self.after_cancel(self._job)
        self._job = self.after(35, self._paint)

    def _paint(self):
        self._job = None
        W, H = self._size
        if W < 10 or H < 10:
            return
        S = self.S
        img = T.linear_gradient(W, H, self.c1, self.c2, self.angle)
        # rounded corners (2x supersampled mask for crisp performance)
        rw, rh = int(W * 2), int(H * 2)
        mask = Image.new("L", (rw, rh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, rw - 1, rh - 1), radius=int(self.radius * S * 2), fill=255)
        mask = mask.resize((W, H), Image.BILINEAR)
        base = Image.new("RGB", (W, H), self.outer_bg)
        base.paste(img, (0, 0), mask)
        self._photo = ImageTk.PhotoImage(base)
        self.delete("all")
        self.create_image(0, 0, image=self._photo, anchor="nw")
        self.layout(self)

    def grad_color_at(self, x_frac: float, y_frac: float) -> str:
        """Approximate gradient colour at a point (used as button 'bg_color' so corners blend in)."""
        t = min(1.0, max(0.0, (x_frac + y_frac) / 2))
        a, b = T._hex(self.c1), T._hex(self.c2)
        c = a * (1 - t) + b * t
        return "#%02x%02x%02x" % tuple(int(v) for v in c)


# --------------------------------------------------------------------------
# KPI card (.kpi-card)
# --------------------------------------------------------------------------
def KpiCard(master, label: str, value: str, accent: str, icon_name: str | None = None, glyph: str | None = None,
            foot: str = "Verified from PDF ledger") -> ctk.CTkFrame:
    outer = ctk.CTkFrame(master, fg_color=T.BORDER, corner_radius=T.R_MD)
    stripe = ctk.CTkFrame(outer, fg_color=accent, corner_radius=T.R_MD, width=16)
    stripe.place(x=0, y=0, relheight=1)
    inner = ctk.CTkFrame(outer, fg_color="#ffffff", corner_radius=T.R_MD - 1, bg_color=T.BORDER)
    inner.pack(fill="both", expand=True, padx=(4, 1), pady=1)
    head = ctk.CTkFrame(inner, fg_color="transparent")
    head.pack(fill="x", padx=16, pady=(14, 0))
    ctk.CTkLabel(head, text=label, font=F("ui6", 12), text_color=T.MUTED).pack(side="left")
    if icon_name:
        ctk.CTkLabel(head, text="", image=T.emoji(icon_name, 15), width=15).pack(side="right")
    else:
        ctk.CTkLabel(head, text=glyph or "", font=F("ui", 14), text_color=T.TEXT2).pack(side="right")
    ctk.CTkLabel(inner, text=value, font=F("brand7", 26), text_color=T.TEXT, anchor="w").pack(fill="x", padx=16, pady=(4, 0))
    ctk.CTkLabel(inner, text=foot, font=F("ui", 11), text_color=T.LIGHT, anchor="w").pack(fill="x", padx=16, pady=(0, 14))
    return outer


def grid_equal(parent, widgets: list, cols: int, gap: int = 14, row_gap: int | None = None, uniform: str = "g"):
    """Lay widgets out in an equal-width grid (CSS grid with repeat(N, 1fr) and a gap)."""
    row_gap = gap if row_gap is None else row_gap
    for c in range(cols):
        parent.grid_columnconfigure(c, weight=1, uniform=uniform)
    for i, w in enumerate(widgets):
        r, c = divmod(i, cols)
        w.grid(row=r, column=c, sticky="nsew", padx=(0 if c == 0 else gap / 2, 0 if c == cols - 1 else gap / 2),
               pady=(0 if r == 0 else row_gap, 0))


def Line(master, color: str, **_ignored) -> tk.Frame:
    """1px divider (CTkFrame cannot render below its minimum height, a plain Tk frame can)."""
    return tk.Frame(master, height=1, bg=color, bd=0, highlightthickness=0)
