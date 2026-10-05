"""Student result card (the .desktop-dialog modal of the web UI)."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import BadgeCell, DataTable, Inline, Line, TwoLine, Txt
from .theme import F


def _val(v):
    return "-" if v is None else v


def open_student_dialog(parent, student: dict, subjects_meta: list[dict]):
    win = ctk.CTkToplevel(parent)
    win.withdraw()
    win.title("Marks Analyser  |  Student Result Card")
    win.configure(fg_color="#ffffff")
    win.resizable(False, False)
    T.set_window_icon(win)
    T.style_titlebar(win)

    body = ctk.CTkFrame(win, fg_color="#ffffff", corner_radius=0, width=680)
    body.pack(fill="both", expand=True)
    pad = dict(padx=24)
    passed = student["result"] == "PASS"

    # ---- header: ledger tag, name, USN · year type, result badge --------------------
    head = ctk.CTkFrame(body, fg_color="transparent")
    head.pack(fill="x", pady=(24, 0), **pad)
    left = ctk.CTkFrame(head, fg_color="transparent")
    left.pack(side="left", fill="x", expand=True)
    ctk.CTkLabel(left, text="OFFICIAL RESULT LEDGER", font=F("brand7", 10), text_color=T.RED, anchor="w").pack(anchor="w")
    ctk.CTkLabel(left, text=student["name"], font=F("ui7", 22), text_color=T.TEXT, anchor="w").pack(anchor="w", pady=(2, 0))
    line = ctk.CTkFrame(left, fg_color="transparent")
    line.pack(anchor="w")
    ctk.CTkLabel(line, text=f"{student['usn']} · ", font=F("mono", 13), text_color=T.MUTED).pack(side="left")
    ctk.CTkLabel(line, text=student["year_type"], font=F("mono6", 13), text_color=T.TEXT).pack(side="left")
    bg, fg = (T.BADGE_PASS_BG, T.BADGE_PASS_TEXT) if passed else (T.BADGE_FAIL_BG, T.BADGE_FAIL_TEXT)
    badge = ctk.CTkFrame(head, fg_color=bg, corner_radius=16)
    badge.pack(side="right", anchor="n")
    ctk.CTkLabel(badge, text=student["result"].upper(), font=F("ui7", 13), text_color=fg).pack(padx=14, pady=6)
    Line(body, T.BORDER).pack(fill="x", pady=(16, 20), **pad)

    # ---- subject table ------------------------------------------------------------------
    meta = {m["code"]: m["name"] for m in subjects_meta}
    cols = [{"title": "Subject", "w": 250, "flex": 3}, {"title": "Theory", "w": 80, "flex": 1},
            {"title": "Internal", "w": 80, "flex": 1}, {"title": "Total", "w": 80, "flex": 1},
            {"title": "Status", "w": 110, "flex": 1}]
    table = DataTable(body, cols, max_height=280, empty_text="No subject marks available.")
    rows = []
    for code, sub in (student.get("subjects") or {}).items():
        rows.append([
            TwoLine(Txt(meta.get(code, code), "ui7", 13), Txt(code, "mono", 10, T.MUTED)),
            Txt(_val(sub.get("theory"))), Txt(_val(sub.get("internal"))), Txt(_val(sub.get("total")), "ui7"),
            BadgeCell(sub.get("status", "-"), "pass" if sub.get("status") == "PASS" else "fail"),
        ])
    table.pack(fill="x", **pad)
    table.set_rows(rows)

    # ---- three stat tiles -----------------------------------------------------------------
    tiles = ctk.CTkFrame(body, fg_color="transparent")
    tiles.pack(fill="x", pady=(20, 0), **pad)
    max_t = int(student.get("max_total") or 700)
    specs = [("Grand Total", str(_val(student["total"])), f" / {max_t}", T.TEXT),
             ("Percentage", pct, "", T.TEXT),
             ("Semester Outcome", student["result"], "", T.BADGE_PASS_TEXT if passed else T.BADGE_FAIL_TEXT)]
    for c, (label, value, suffix, color) in enumerate(specs):
        tiles.grid_columnconfigure(c, weight=1, uniform="tile")
        tile = ctk.CTkFrame(tiles, fg_color=T.CANVAS_BG, border_width=1, border_color=T.BORDER, corner_radius=T.R_MD)
        tile.grid(row=0, column=c, sticky="nsew", padx=(0 if c == 0 else 6, 0 if c == 2 else 6))
        ctk.CTkLabel(tile, text=label, font=F("ui", 11), text_color=T.MUTED, anchor="w").pack(fill="x", padx=12, pady=(10, 0))
        row = ctk.CTkFrame(tile, fg_color="transparent")
        row.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(row, text=value, font=F("brand7", 20), text_color=color).pack(side="left")
        if suffix:
            ctk.CTkLabel(row, text=suffix, font=F("ui", 12), text_color=T.LIGHT).pack(side="left", pady=(5, 0))

    # ---- SGPA / CGPA / Class footer -------------------------------------------------------
    foot = ctk.CTkFrame(body, fg_color="#f1f5f9", corner_radius=T.R_MD)
    foot.pack(fill="x", pady=(16, 24), **pad)
    inner = ctk.CTkFrame(foot, fg_color="transparent")
    inner.pack(fill="x", padx=14, pady=10)
    items = [("SGPA: ", student.get("sgpa") or "-"), ("CGPA: ", student.get("cgpa") or "-"),
             ("Class: ", student.get("grade") or "Not exposed")]
    for i, (label, value) in enumerate(items):
        cell = ctk.CTkFrame(inner, fg_color="transparent")
        cell.pack(side="left" if i == 0 else ("right" if i == 2 else "left"), **({"expand": True} if i == 1 else {}))
        ctk.CTkLabel(cell, text=label, font=F("ui", 12), text_color=T.TEXT2).pack(side="left")
        ctk.CTkLabel(cell, text=str(value), font=F("ui7", 12), text_color=T.TEXT2).pack(side="left")

    # ---- show centred over the main window, modal, Esc closes -----------------------------
    win.update_idletasks()
    s = T.scale_of(win)
    w, h = max(int(680 * s), win.winfo_reqwidth()), win.winfo_reqheight()
    px, py = parent.winfo_rootx() + parent.winfo_width() // 2, parent.winfo_rooty() + parent.winfo_height() // 2
    win.geometry(f"{int(w / s)}x{int(h / s)}+{max(0, int(px - w / 2))}+{max(0, int(py - h / 2))}")
    win.transient(parent)
    win.deiconify()
    win.bind("<Escape>", lambda e: win.destroy())
    win.after(120, lambda: (win.winfo_exists() and (win.grab_set(), win.focus_force())))
    return win
