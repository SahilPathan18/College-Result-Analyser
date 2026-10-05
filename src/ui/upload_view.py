"""Launch / upload screen (the .desktop-launcher card of the web UI)."""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import filedialog
from typing import Callable

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageTk

from . import theme as T
from .components import Line, AppButton
from .theme import F, TkF, scale_of


def _spinner_frames(size: int = 14, n: int = 12) -> list[ctk.CTkImage]:
    big = size * 8
    frames = []
    for i in range(n):
        im = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        w = int(big * 2 / size * 1.0)
        box = (w // 2, w // 2, big - w // 2, big - w // 2)
        d.ellipse(box, outline=(255, 255, 255, 80), width=w)
        start = -90 + i * (360 / n)
        d.arc(box, start, start + 100, fill=(255, 255, 255, 255), width=w)
        frames.append(ctk.CTkImage(light_image=im, dark_image=im, size=(size, size)))
    return frames


class UploadView(tk.Canvas):
    def __init__(self, master, on_analyze: Callable[[str], None], dnd: bool = False):
        super().__init__(master, highlightthickness=0, bd=0, bg=T.WIN_BG)
        self.on_analyze = on_analyze
        self.dnd = dnd
        self.path: str | None = None
        self._bgphoto = None
        self._size = (0, 0)
        self._busy = False
        self._spin_job = None
        self._spin_i = 0
        self._spinner = None
        self._hover = False

        # ---- the white launcher card ------------------------------------------------
        self.card = ctk.CTkFrame(self, fg_color="#ffffff", corner_radius=T.R_XL, bg_color="#18253a",
                                 border_width=1, border_color="#334155")
        self.card.bind("<Configure>", lambda e: self._schedule_paint(), add="+")
        ctk.CTkLabel(self.card, text="", image=T.logo(72)).pack(pady=(44, 0))
        ctk.CTkLabel(self.card, text="Marks Analyser", font=F("brand", 36), text_color=T.TEXT
                     ).pack(pady=(20, 24))

        S = scale_of(self)
        self.zone_w, self.zone_h = 536, 196
        self.zone = tk.Canvas(self.card, width=int(self.zone_w * S), height=int(self.zone_h * S),
                              bg="#ffffff", highlightthickness=0, bd=0, cursor="hand2")
        self.zone.pack(padx=42)
        self.zone.bind("<Button-1>", lambda e: self.browse())
        self.zone.bind("<Enter>", lambda e: self._set_hover(True))
        self.zone.bind("<Leave>", lambda e: self._set_hover(False))
        self.meta_parts = [("Supports official university ledger PDFs · Processed securely in memory", False)]
        self._draw_zone()

        self.error = ctk.CTkLabel(self.card, text="", font=F("ui6", 12), text_color=T.RED, height=24,
                                  wraplength=520)
        self.error.pack(pady=(10, 0), padx=42)

        self.arrow = T.icon("arrow_white", 18)
        self.btn = AppButton(self.card, "Run Marks Analyser", "primary", self._submit, image=self.arrow,
                             compound="right", height=46, size=15, state="disabled", text_color_disabled="#ffffff")
        self.btn.pack(fill="x", padx=42, pady=(16, 44))

        self._win = self.create_window(0, 0, window=self.card, anchor="center")
        self.bind("<Configure>", self._on_configure)
        self._register_dnd()

    # ---- background ----------------------------------------------------------------
    def _on_configure(self, e):
        if (e.width, e.height) == self._size or e.width < 10 or e.height < 10:
            return
        self._size = (e.width, e.height)
        if getattr(self, "_paint_job", None):
            self.after_cancel(self._paint_job)
        self._paint_job = self.after(30, self._rebuild_and_paint)

    def _schedule_paint(self):
        ch = max(self.card.winfo_reqheight(), 10)
        if getattr(self, "_last_card_h", None) == ch:
            return
        self._last_card_h = ch
        if getattr(self, "_paint_job", None):
            self.after_cancel(self._paint_job)
        self._paint_job = self.after(30, self._paint_bg)

    def _rebuild_and_paint(self):
        self._paint_job = None
        W, H = self._size
        if W < 10 or H < 10:
            return
        small = T.radial_gradient(max(8, W // 5), max(8, H // 5), "#1e293b", "#0b101d", .5, .15)
        self._grad = small.resize((W, H), Image.BICUBIC)
        self._paint_bg()

    def _paint_bg(self):
        self._paint_job = None
        if not getattr(self, "_grad", None):
            return
        W, H = self._size
        if W < 10 or H < 10:
            return
        img = self._grad.copy()
        self._bgphoto = ImageTk.PhotoImage(img)
        self.delete("bg")
        self.create_image(0, 0, image=self._bgphoto, anchor="nw", tags="bg")
        self.tag_lower("bg")
        ch = max(self.card.winfo_reqheight(), 10)
        cx, cy = W / 2, max(H / 2, ch / 2 + 10)
        curr_coords = self.coords(self._win)
        if not curr_coords or abs(curr_coords[0] - cx) > 1 or abs(curr_coords[1] - cy) > 1:
            self.coords(self._win, cx, cy)

    # ---- drop zone -----------------------------------------------------------------
    def _set_hover(self, state: bool):
        self._hover = state
        self._draw_zone()

    def _draw_zone(self):
        c, S = self.zone, scale_of(self.zone)
        c.delete("all")
        W, H = self.zone_w * S, self.zone_h * S
        border = T.RED if self._hover else "#cbd5e1"
        fill = "#fff5f5" if self._hover else "#f8fafc"
        T.round_rect(c, 2 * S, 2 * S, W - 2 * S, H - 2 * S, T.R_LG * S, fill=fill, outline=border,
                     width=max(2, round(2 * S)), dash=(int(7 * S), int(5 * S)))
        self._zone_icon = ImageTk.PhotoImage(T.pil_icon("fileplus_red").resize((int(40 * S), int(40 * S)), Image.LANCZOS))
        c.create_image(W / 2, 56 * S, image=self._zone_icon)
        c.create_text(W / 2, 99 * S, text="Import Result PDF", font=TkF("ui7", 18, S), fill=T.TEXT)

        f1, f2 = TkF("ui", 13, S), TkF("ui7", 13, S)
        link_font = tkfont.Font(**f2.actual())
        link_font.configure(underline=True)
        self._link_font = link_font
        lead = ("Drag and drop your official result ledger here, or " if self.dnd
                else "Select your official result ledger PDF here, or ")
        w1, w2 = f1.measure(lead), f2.measure("Browse Local File")
        x = (W - w1 - w2) / 2
        y = 125 * S
        c.create_text(x, y, text=lead, anchor="w", font=f1, fill=T.TEXT2)
        c.create_text(x + w1, y, text="Browse Local File", anchor="w", font=link_font, fill=T.RED)

        # file meta line: "<b>name</b> · 1.20 MB" or the default hint
        fm, fb = TkF("ui", 11, S), TkF("ui7", 11, S)
        parts = self.meta_parts
        total = sum((fb if b else fm).measure(t) for t, b in parts)
        x = (W - total) / 2
        for text, bold in parts:
            font = fb if bold else fm
            c.create_text(x, 152 * S, text=text, anchor="w", font=font, fill=T.MUTED if not bold else T.TEXT)
            x += font.measure(text)

    # ---- actions ---------------------------------------------------------------------
    def browse(self):
        if self._busy:
            return
        path = filedialog.askopenfilename(title="Select Result PDF", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.set_file(path)

    def set_file(self, path: str):
        p = Path(path)
        try:
            size = p.stat().st_size
        except OSError:
            size = 0
        if p.suffix.lower() != ".pdf" or not size:
            self.path = None
            self.error.configure(text="Invalid file. Please select a valid, non-empty university result PDF.")
            self.btn.configure(state="disabled")
            return
        self.path = str(p)
        self.error.configure(text="")
        name = p.name if len(p.name) < 60 else p.name[:57] + "…"
        self.meta_parts = [(name, True), (f" · {size / 1024 / 1024:.2f} MB", False)]
        self._draw_zone()
        self.btn.configure(state="normal")

    def _submit(self):
        if self.path and not self._busy:
            self.error.configure(text="")
            self.on_analyze(self.path)

    def set_busy(self, busy: bool):
        self._busy = busy
        if busy:
            self.btn.configure(state="disabled", text="Analyzing Result Ledger...  ")
            self._spinner = self._spinner or _spinner_frames()
            self._spin()
        else:
            if self._spin_job:
                self.after_cancel(self._spin_job)
                self._spin_job = None
            self.btn.configure(text="Run Marks Analyser", image=self.arrow, state="normal" if self.path else "disabled")

    def _spin(self):
        if not self._busy:
            return
        self.btn.configure(image=self._spinner[self._spin_i % len(self._spinner)])
        self._spin_i += 1
        self._spin_job = self.after(70, self._spin)

    def show_error(self, message: str):
        self.error.configure(text=message)

    def reset(self):
        self.path = None
        self.meta_parts = [("Supports official university ledger PDFs · Processed securely in memory", False)]
        self.error.configure(text="")
        self.btn.configure(state="disabled")
        self._draw_zone()

    # ---- optional drag & drop (tkinterdnd2) ---------------------------------------------
    def _register_dnd(self):
        if not self.dnd:
            return
        try:
            from tkinterdnd2 import DND_FILES

            def drop(event):
                files = self.tk.splitlist(event.data)
                if files:
                    self.set_file(files[0])
                self._set_hover(False)
                return event.action

            for w in (self.zone, self.card):
                w.drop_target_register(DND_FILES)
                w.dnd_bind("<<Drop>>", drop)
                w.dnd_bind("<<DropEnter>>", lambda e: self._set_hover(True))
                w.dnd_bind("<<DropLeave>>", lambda e: self._set_hover(False))
        except Exception:
            self.dnd = False
            self._draw_zone()
