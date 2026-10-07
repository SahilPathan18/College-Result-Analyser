"""TAB 6 - Backlogs (year-type analysis)."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import BadgeCell, Card, DataTable, Txt, card_head, grid_equal
from .theme import F


def build(body, data: dict, shell):
    cur, summary = data["current"], data["summary"]
    wrap = ctk.CTkFrame(body, fg_color="transparent")
    wrap.pack(fill="x")

    left = Card(wrap)
    card_head(left, "Current-Year Performance", "Fresh regular candidates", hint_size=12).pack(fill="x", padx=20, pady=(20, 6))
    tiles = ctk.CTkFrame(left, fg_color="transparent")
    tiles.pack(fill="x", padx=20, pady=(10, 20))
    spec = [(cur["total"], "Total Registered", T.TEXT), (cur["attended"], "Attended", T.TEXT),
            (cur["passed"], "Passed", T.GREEN), (cur["failed"], "Failed", T.RED),
            (f"{cur['pass_percentage']}%", "Pass Rate", T.TEXT), (f"{cur['average_percentage']}%", "Class Average", T.TEXT)]
    widgets = []
    for value, label, color in spec:
        tile = ctk.CTkFrame(tiles, fg_color=T.CANVAS_BG, border_width=1, border_color=T.BORDER, corner_radius=T.R_MD)
        ctk.CTkLabel(tile, text=str(value), font=F("brand", 24), text_color=color, anchor="w").pack(fill="x", padx=16, pady=(14, 0))
        ctk.CTkLabel(tile, text=label, font=F("ui", 11), text_color=T.MUTED, anchor="w").pack(fill="x", padx=16, pady=(0, 14))
        widgets.append(tile)
    grid_equal(tiles, widgets, 3, gap=14, uniform="tile")

    right = Card(wrap)
    card_head(right, "Backlog & Repeater Students", f"{summary.get('backlog', 0)} candidates flagged", hint_size=12
              ).pack(fill="x", padx=20, pady=(20, 16))
    cols = [{"title": "Register Number", "w": 140, "flex": 1}, {"title": "Student Name", "w": 140, "flex": 2},
            {"title": "Status", "w": 100, "flex": 0}, {"title": "Percentage", "w": 100, "flex": 0}]
    table = DataTable(right, cols, max_height=520, pad_x=10, empty_text="No backlog records present.")
    table.pack(fill="x", padx=20, pady=(0, 20))
    rows = []
    for s in data.get("backlog_students", []):
        res = str(s["result"])
        kind = "pass" if res == "PASS" else ("fail" if res == "FAIL" else "plain")
        pct = s["percentage"]
        rows.append([Txt(s["usn"]), Txt(s["name"]), BadgeCell(res, kind), Txt(pct if pct == "-" else f"{pct}%")])
    table.set_rows(rows)

    grid_equal(wrap, [left, right], 2, gap=18, uniform="cohort")
