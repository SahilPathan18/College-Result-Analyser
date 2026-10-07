"""TAB 7 - Export & Reports."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import AppButton, Card, GradientCanvas, card_head
from .theme import F, TkF

LEAD = ("Exports complete current-year register analysis with auto-formatted worksheets for Summary, "
        "Student Results, Subject Analytics, Failed Students, and Toppers.")


def build(body, data: dict, shell):
    def layout(c: GradientCanvas):
        S = c.S
        W, H = c.winfo_width(), c.winfo_height()
        x = 32 * S
        c.create_text(x, 36 * S + 6 * S, text="READY FOR EXPORT", anchor="w", fill=T.RED, font=TkF("ui7", 10, S))
        c.create_text(x, 66 * S, text="Generate Comprehensive Excel Workbook", anchor="w", fill="#ffffff", font=TkF("ui7", 22, S))
        if not hasattr(c, "_btn"):
            c._btn = AppButton(c, "Download Excel Report (.xlsx)", "primary", shell.export_excel,
                               image=T.icon("download_white_bold", 20), height=48, size=14, radius=T.R_MD,
                               bg_color=c.grad_color_at(.9, .5))
        btn_w = c._btn.winfo_reqwidth() if c._btn.winfo_reqwidth() > 10 else int(280 * S)
        text_max_w = max(int(240 * S), int(W - btn_w - 72 * S))
        c.create_text(x, 90 * S, text=LEAD, anchor="nw", fill="#94a3b8", font=TkF("ui", 13, S), width=text_max_w)
        fx = x
        font = TkF("ui", 12, S)
        for label in ("✓ Formatted Excel (.xlsx)", "✓ Complete Mark Breakdown", "✓ Filter & Rank Columns"):
            c.create_text(fx, 160 * S, text=label, anchor="w", fill="#cbd5e1", font=font)
            fx += font.measure(label) + 16 * S
        c.create_window(W - 32 * S, H / 2, window=c._btn, anchor="e")

    hero = GradientCanvas(body, "#090d16", "#1e293b", 200, layout)
    hero.pack(fill="x", pady=(0, 20))

    warnings = data.get("warnings") or []
    if warnings:
        card = Card(body)
        card.pack(fill="x")
        card_head(card, "Ledger Integrity & Validation Warnings", f"{len(warnings)} items identified",
                  hint_color=T.TEXT, hint_size=12).pack(fill="x", padx=20, pady=(20, 16))
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="x", padx=20, pady=(0, 20))

        def add(start=0):                       # built in chunks so very long lists never freeze the UI
            for w in warnings[start:start + 25]:
                row = ctk.CTkFrame(box, fg_color="#fffbeb", border_width=1, border_color="#fef3c7", corner_radius=T.R_SM)
                row.pack(fill="x", pady=(0, 8))
                ctk.CTkLabel(row, text=f"⚠  {w}", font=F("ui", 12), text_color="#92400e", anchor="w"
                             ).pack(fill="x", padx=14, pady=8)
            if start + 25 < len(warnings):
                box.after(15, add, start + 25)
        add()
