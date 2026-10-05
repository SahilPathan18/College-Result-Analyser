"""TAB 5 - Toppers & Merit."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import Line, BadgeCell, Card, DataTable, Inline, Pill, Txt, card_head, grid_equal, section_intro
from .theme import F

MEDALS = ["gold", "silver", "bronze"]
PLACES = ["1ST PLACE", "2ND PLACE", "3RD PLACE"]


def _podium_slot(parent, rank: int, t: dict):
    first = rank == 0
    slot = ctk.CTkFrame(parent, fg_color="#fffdf5" if first else "#ffffff", border_width=1,
                        border_color="#fde68a" if first else T.BORDER, corner_radius=T.R_LG)
    ctk.CTkLabel(slot, text="", image=T.emoji(MEDALS[rank], 32)).pack(pady=(24, 4))
    ctk.CTkLabel(slot, text=PLACES[rank], font=F("ui7", 11), text_color=T.AMBER).pack(pady=(0, 8))
    ctk.CTkLabel(slot, text=t["name"], font=F("ui7", 16), text_color=T.TEXT).pack(padx=18)
    ctk.CTkLabel(slot, text=t["usn"], font=F("mono", 12), text_color=T.MUTED).pack(pady=(4, 12))
    marks = ctk.CTkFrame(slot, fg_color="transparent")
    marks.pack()
    max_t = int(t.get("max_total") or 700)
    ctk.CTkLabel(marks, text=str(t["total"]), font=F("brand", 26), text_color=T.TEXT).pack(side="left")
    ctk.CTkLabel(marks, text=f" / {max_t}", font=F("ui", 12), text_color=T.MUTED).pack(side="left", pady=(8, 0))
    Pill(slot, f"{t['percentage']}%", "#fef3c7", "#92400e", "ui7", 12, 10, 3, 12,
         outer_bg=slot.cget("fg_color")).pack(pady=(8, 24))
    return slot


def build(body, data: dict, shell):
    toppers = data["toppers"]
    section_intro(body, "Academic Honors & Merit Toppers",
                  "Current-year overall pass students ranked by grand total score.", center=True
                  ).pack(fill="x", pady=(0, 0))

    pod = ctk.CTkFrame(body, fg_color="transparent")
    pod.pack(fill="x", pady=(20, 28))
    if toppers:
        top3 = toppers[:3]
        for c in range(3):
            pod.grid_columnconfigure(c, weight=1, uniform="pod")
        for i, t in enumerate(top3):
            slot = _podium_slot(pod, i, t)
            # rank-1 is lifted 8px (transform: translateY(-8px)); all slots share a bottom edge
            slot.grid(row=0, column=i, sticky="s", padx=(0 if i == 0 else 8, 0 if i == len(top3) - 1 else 8),
                      pady=(0, 8) if i == 0 else (8, 0))
            slot.grid_configure(sticky="sew")
    else:
        ctk.CTkLabel(pod, text="No eligible topper records found.", font=F("ui", 13), text_color=T.MUTED
                     ).pack(pady=24)

    split = ctk.CTkFrame(body, fg_color="transparent")
    split.pack(fill="x")

    # ---- Top 10 table ---------------------------------------------------------------------
    left = Card(split)
    card_head(left, "Top 10 Rankers (Overall)").pack(fill="x", padx=20, pady=(20, 16))
    cols = [{"title": "Rank", "w": 60, "flex": 0}, {"title": "Name", "w": 130, "flex": 2},
            {"title": "USN", "w": 120, "flex": 1}, {"title": "Total", "w": 100, "flex": 1},
            {"title": "Percentage", "w": 100, "flex": 0}]
    table = DataTable(left, cols, max_height=520, pad_x=10, empty_text="No eligible topper records found.")
    table.pack(fill="x", padx=20, pady=(0, 20))
    table.set_rows([[Txt(f"#{i}", "ui7"), Txt(t["name"]), Txt(t["usn"]),
                     Inline(Txt(t["total"], "ui7"), Txt(f"/ {int(t.get('max_total') or 700)}")), BadgeCell(f"{t['percentage']}%", "pass")]
                    for i, t in enumerate(toppers, 1)])

    # ---- subject-wise high achievers --------------------------------------------------------
    right = Card(split)
    card_head(right, "Subject-wise High Achievers").pack(fill="x", padx=20, pady=(20, 16))
    groups = data["subject_toppers"]
    for gi, s in enumerate(groups):
        g = ctk.CTkFrame(right, fg_color="transparent")
        g.pack(fill="x", padx=20, pady=(0, 16 if gi < len(groups) - 1 else 20))
        hdr = ctk.CTkFrame(g, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 8))
        ctk.CTkLabel(hdr, text=s["code"], font=F("mono7", 11), text_color=T.RED).pack(side="left")
        ctk.CTkLabel(hdr, text=s["name"], font=F("ui7", 14), text_color=T.TEXT).pack(side="left", padx=(8, 0))
        if not s["toppers"]:
            ctk.CTkLabel(g, text="No toppers recorded.", font=F("ui", 13), text_color=T.MUTED).pack(pady=12)
        for i, t in enumerate(s["toppers"]):
            row = ctk.CTkFrame(g, fg_color="transparent")
            row.pack(fill="x", pady=6)
            ctk.CTkLabel(row, text="", image=T.emoji(MEDALS[i], 16), width=20).pack(side="left")
            info = ctk.CTkFrame(row, fg_color="transparent")
            info.pack(side="left", padx=(10, 0), fill="x", expand=True)
            ctk.CTkLabel(info, text=t["name"], font=F("ui6", 13), text_color=T.TEXT, anchor="w").pack(anchor="w")
            ctk.CTkLabel(info, text=f"{t['usn']} · Th: {t.get('theory')} | In: {t.get('internal')}", font=F("ui", 11),
                         text_color=T.MUTED, anchor="w").pack(anchor="w")
            ctk.CTkLabel(row, text=str(t.get("total")), font=F("brand7", 15), text_color=T.TEXT).pack(side="right")
        if gi < len(groups) - 1:
            Line(g, T.BORDER_SUBTLE).pack(fill="x", pady=(12, 0))
    grid_equal(split, [left, right], 2, gap=18, uniform="split")
    left.grid_configure(sticky="nsew")
