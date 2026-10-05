"""TAB 3 - Subject Analysis cards."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import Card, grid_equal, rich, section_intro
from .theme import F


def _subject_card(parent, s: dict):
    card = ctk.CTkFrame(parent, fg_color="#ffffff", border_width=1, border_color=T.BORDER, corner_radius=T.R_LG)
    ctk.CTkLabel(card, text=s["code"], font=F("mono7", 11), text_color=T.RED, anchor="w").pack(fill="x", padx=18, pady=(18, 6))
    name = ctk.CTkLabel(card, text=s["name"], font=F("ui7", 15), text_color=T.TEXT, anchor="nw", justify="left",
                        height=40, wraplength=260)
    name.pack(fill="x", padx=18, pady=(0, 14))

    def _on_card_configure(e):
        target_wrap = max(120, int(e.width / T.scale_of(card)) - 40)
        if getattr(name, "_last_wrap", None) != target_wrap:
            name._last_wrap = target_wrap
            name.configure(wraplength=target_wrap)

    card.bind("<Configure>", _on_card_configure, add="+")

    metrics = ctk.CTkFrame(card, fg_color="transparent")
    metrics.pack(fill="x", padx=18, pady=(0, 12))
    for c, (val, label, color) in enumerate([(s["appeared"], "Appeared", T.TEXT), (s["passed"], "Passed", T.GREEN),
                                             (s["failed"], "Failed", T.RED), (s["absent"], "Absent", T.AMBER)]):
        metrics.grid_columnconfigure(c, weight=1, uniform="m")
        col = ctk.CTkFrame(metrics, fg_color="transparent")
        col.grid(row=0, column=c, sticky="w", padx=(0 if c == 0 else 4, 4))
        ctk.CTkLabel(col, text=str(val), font=F("ui7", 16), text_color=color, anchor="w").pack(anchor="w")
        ctk.CTkLabel(col, text=label.upper(), font=F("ui", 10), text_color=T.MUTED, anchor="w").pack(anchor="w")

    bar = ctk.CTkProgressBar(card, height=6, corner_radius=4, fg_color="#e2e8f0", progress_color=T.GREEN, border_width=0)
    bar.set(max(0.0, min(1.0, float(s["pass_percentage"]) / 100)))
    bar.pack(fill="x", padx=18, pady=(0, 12))

    foot = ctk.CTkFrame(card, fg_color="transparent")
    foot.pack(fill="x", padx=18, pady=(0, 18))
    rich(foot, [(f"{s['pass_percentage']}%", "ui7", 11, T.TEXT2), (" Pass Rate", "ui", 11, T.TEXT2)]).pack(side="left")
    rich(foot, [("Max: ", "ui", 11, T.TEXT2), (str(s["highest"]), "ui7", 11, T.TEXT2)]).pack(side="right")
    rich(foot, [("Avg: ", "ui", 11, T.TEXT2), (str(s["average"]), "ui7", 11, T.TEXT2)]).pack(side="left", expand=True)
    return card


def build(body, data: dict, shell):
    sem = data.get("metadata", {}).get("semester")
    sem_str = f" in Semester {sem}" if sem else ""
    section_intro(body, "Subject Performance Breakdown",
                  f"Detailed performance statistics across all {len(data['subjects'])} evaluated subjects{sem_str}.").pack(fill="x", pady=(0, 20))
    grid = ctk.CTkFrame(body, fg_color="transparent")
    grid.pack(fill="x")
    grid_equal(grid, [_subject_card(grid, s) for s in data["subjects"]], 3, gap=16, uniform="subj")
