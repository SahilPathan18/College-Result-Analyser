"""TAB 1 - Overview dashboard."""
from __future__ import annotations

import tkinter.font as tkfont

import customtkinter as ctk

from . import theme as T
from .charts import ChartWidget
from .components import AppButton, Card, GradientCanvas, KpiCard, card_head, grid_equal
from .theme import F, TkF


def build(body, data: dict, shell) -> None:
    summary = data["summary"]

    # ---- KPI cards ------------------------------------------------------------------
    spec = [
        ("total", "Total Students", T.BLUE, "users", None),
        ("attended", "Attended", T.CYAN, None, "✓"),
        ("passed", "Passed", T.GREEN, "grad", None),
        ("failed", "Failed", T.RED, None, "✕"),
        ("pass_percentage", "Pass Percentage", T.AMBER, None, "%"),
        ("fail_percentage", "Fail Percentage", T.ORANGE, "chart_down", None),
    ]
    grid = ctk.CTkFrame(body, fg_color="transparent")
    grid.pack(fill="x", pady=(0, 20))
    cards = []
    for key, label, color, emo, glyph in spec:
        value = f"{summary[key]}" + ("%" if "percentage" in key else "")
        cards.append(KpiCard(grid, label, value, color, icon_name=emo, glyph=glyph))
    grid_equal(grid, cards, 3, gap=14, uniform="kpi")

    # ---- "Result Intelligence" banner ----------------------------------------------
    def layout(c: GradientCanvas):
        S = c.S
        W, H = c.winfo_width(), c.winfo_height()
        x = 32 * S
        prog = data.get("metadata", {}).get("program") or "University"
        sem = data.get("metadata", {}).get("semester") or ""
        snap_title = f"{prog} {('Semester ' + sem) if sem else ''} Result Snapshot".strip()
        c.create_text(x, 60 * S, text=snap_title, anchor="w", fill="#ffffff",
                      font=TkF("ui7", 22, S))
        c.create_text(x, 82 * S,
                      text=("Full academic performance synthesized directly from official registers. Inspect "
                            "students, identify subjects needing remediation, and celebrate top achievers."),
                      anchor="nw", fill="#94a3b8", font=TkF("ui", 13, S), width=520 * S)
        if not hasattr(c, "_btns"):
            c._btns = (
                AppButton(c, "Browse Student Register  →", "primary", lambda: shell.show("students"),
                          bg_color=c.grad_color_at(.1, .8)),
                AppButton(c, "Subject Diagnostics", "outline", lambda: shell.show("subjects"),
                          bg_color=c.grad_color_at(.2, .8)),
            )
        b1, b2 = c._btns
        by = 137 * S
        c.create_window(x, by, window=b1, anchor="nw")
        c.create_window(x + b1.winfo_reqwidth() + 10 * S, by, window=b2, anchor="nw")
        # orbit circle
        r = 70 * S
        cx, cy = W - 32 * S - r, H / 2
        c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=T.blend("#ffffff", .05, c.grad_color_at(.85, .5)),
                      outline=T.blend("#ffffff", .20, c.grad_color_at(.85, .5)), width=max(2, round(2 * S)),
                      dash=(int(5 * S), int(4 * S)))
        c.create_text(cx, cy - 8 * S, text=str(summary["total"]), fill="#ffffff", font=TkF("brand", 38, S))
        c.create_text(cx, cy + 28 * S, text="Students Analyzed", fill="#94a3b8", font=TkF("ui", 11, S))

    banner = GradientCanvas(body, "#0f172a", "#1e293b", 200, layout)
    banner.pack(fill="x", pady=(0, 20))

    # ---- charts ----------------------------------------------------------------------
    subjects = data["subjects"]
    labels = [s["name"] if len(s["name"]) <= 20 else s["name"][:18] + "..." for s in subjects]

    def chart_card(parent, title, hint, kind, values, color, suffix=""):
        card = Card(parent)
        head = card_head(card, title, hint)
        head.pack(fill="x", padx=20, pady=(20, 16))
        holder = ctk.CTkFrame(card, fg_color="#ffffff", corner_radius=0)
        holder.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        chart = ChartWidget(holder, kind, labels, values, color, height=240, suffix=suffix)
        chart.widget.pack(fill="both", expand=True)
        card._chart = chart
        return card

    row = ctk.CTkFrame(body, fg_color="transparent")
    row.pack(fill="x")
    c1 = chart_card(row, "Pass Percentage by Subject", "Success rate %", "bar",
                    [s["pass_percentage"] for s in subjects], T.BLUE, suffix="%")
    c2 = chart_card(row, "Average Marks by Subject", "Class mean score", "line",
                    [s["average"] for s in subjects], T.GREEN)
    grid_equal(row, [c1, c2], 2, gap=16, uniform="chart")
    wide = chart_card(body, "Failed Students by Subject", "Immediate remediation", "bar",
                      [s["failed"] for s in subjects], T.RED)
    wide.pack(fill="x", pady=(16, 0))
