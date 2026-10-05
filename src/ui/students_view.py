"""TAB 2 - Student Register (search / filter / sort / pagination / detail dialog)."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import (AppButton, BadgeCell, Card, DataTable, Inline, Pagination, SearchBox, Select, Txt)
from .student_dialog import open_student_dialog

PAGE_SIZE = 12
RESULT_OPTIONS = {"All Results (Pass/Fail)": "ALL", "Passed Only": "PASS", "Failed Only": "FAIL"}
YEAR_OPTIONS = {"All Types": "ALL", "Current Year": "Current Year", "Backlog / Repeater": "Backlog / Repeater"}
SORT_OPTIONS = {"Sort: Grand Total": "total", "Sort: Percentage": "percentage", "Sort: Student Name": "name"}


class StudentsView:
    def __init__(self, body, data: dict, shell):
        self.students = data["students"]
        self.subjects = data["subjects"]
        self.shell = shell
        self.page = 1

        card = Card(body)
        card.pack(fill="x")

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.pack(fill="x", padx=20, pady=(20, 14))
        self.search = SearchBox(bar, "Search student name or register number (USN)...", self._changed)
        self.search.pack(side="left", fill="x", expand=True, padx=(0, 14))
        group = ctk.CTkFrame(bar, fg_color="transparent")
        group.pack(side="right")
        self.result_sel = Select(group, list(RESULT_OPTIONS), self._changed, width=190)
        self.year_sel = Select(group, list(YEAR_OPTIONS), self._changed, width=150)
        self.sort_sel = Select(group, list(SORT_OPTIONS), self._changed, width=170)
        for i, w in enumerate((self.result_sel, self.year_sel, self.sort_sel)):
            w.pack(side="left", padx=(0 if i == 0 else 10, 0))

        cols = [
            {"title": "Rank", "w": 70, "flex": 0},
            {"title": "Register Number", "w": 150, "flex": 1},
            {"title": "Student Name", "w": 200, "flex": 2},
            {"title": "Grand Total", "w": 120, "flex": 1},
            {"title": "Percentage", "w": 110, "flex": 1},
            {"title": "Result Status", "w": 130, "flex": 1},
            {"title": "Year Type", "w": 150, "flex": 1},
        ]
        self.table = DataTable(card, cols, max_height=520, on_click=self._open, empty_text="No matching student records found.")
        self.table.pack(fill="x", padx=20)
        self.pager = Pagination(card, self._prev, self._next)
        self.pager.pack(fill="x", padx=20, pady=(14, 20))
        self._paged: list[dict] = []
        self._render()

    # ---- filtering / sorting (port of getFilteredStudents) ---------------------------
    def _filtered(self) -> list[dict]:
        q = self.search.get().lower().strip()
        rf = RESULT_OPTIONS[self.result_sel.get()]
        yf = YEAR_OPTIONS[self.year_sel.get()]
        sv = SORT_OPTIONS[self.sort_sel.get()]
        rows = [s for s in self.students
                if (not q or q in (s["name"] or "").lower() or q in (s["usn"] or "").lower())
                and (rf == "ALL" or s["result"] == rf)
                and (yf == "ALL" or s["year_type"] == yf)]
        if sv == "name":
            rows.sort(key=lambda s: (s["name"] or "").casefold())
        elif sv == "percentage":
            rows.sort(key=lambda s: s["percentage"] or 0, reverse=True)
        else:
            rows.sort(key=lambda s: s["total"] or 0, reverse=True)
        return rows

    def _changed(self):
        self.page = 1
        self._render()

    def _render(self):
        rows = self._filtered()
        pages = max(1, -(-len(rows) // PAGE_SIZE))
        self.page = min(self.page, pages)
        start = (self.page - 1) * PAGE_SIZE
        self._paged = rows[start:start + PAGE_SIZE]
        out = []
        for idx, s in enumerate(self._paged):
            pct = f"{s['percentage']}%" if s["percentage"] is not None else "-"
            max_t = int(s.get("max_total") or 700)
            out.append([
                Txt(f"#{start + idx + 1}", "ui7"),
                Txt(s["usn"], "mono6"),
                Txt(s["name"], "ui7"),
                Inline(Txt(s["total"], "ui7"), Txt(f"/ {max_t}", "ui", 11, T.LIGHT)),
                Txt(pct, "ui7"),
                BadgeCell(s["result"], "pass" if s["result"] == "PASS" else "fail"),
                Txt(s["year_type"], "ui", 12, T.MUTED),
            ])
        self.table.set_rows(out)
        self.pager.set_label(f"Page {self.page} of {pages} ({len(rows)} students)")

    def _prev(self):
        if self.page > 1:
            self.page -= 1
            self._render()

    def _next(self):
        pages = -(-len(self._filtered()) // PAGE_SIZE)
        if self.page < pages:
            self.page += 1
            self._render()

    def _open(self, row_index: int):
        if 0 <= row_index < len(self._paged):
            open_student_dialog(self.shell.winfo_toplevel(), self._paged[row_index], self.subjects)


def build(body, data, shell):
    return StudentsView(body, data, shell)
