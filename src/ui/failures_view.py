"""TAB 4 - Failed students (comprehensive register + subject-wise remedial + multiple-subject backlogs)."""
from __future__ import annotations

import customtkinter as ctk

from . import theme as T
from .components import BadgeCell, Card, CountCell, DataTable, Select, Txt, WrapCell, card_head, grid_equal
from .student_dialog import open_student_dialog
from .theme import F


def build(body, data: dict, shell):
    subjects = data["subjects"]
    failures = data["subject_failures"]
    all_students = data["students"]
    courses = data.get("courses", subjects)
    course_map = {c["code"]: c["name"] for c in courses}
    students_by_usn = {s["usn"]: s for s in all_students}

    # Identify all failed students across the entire batch
    failed_students = [s for s in all_students if s.get("result") != "PASS"]

    # Statistics strip for executive clarity
    total_failed = len(failed_students)
    multi_count = len(data.get("multiple_failures", []))
    single_count = max(0, total_failed - multi_count)

    # Most affected subject
    fail_counts_by_code = {c["code"]: len(failures.get(c["code"], [])) for c in subjects}
    top_failed_code = max(fail_counts_by_code, key=fail_counts_by_code.get) if fail_counts_by_code else ""
    top_failed_count = fail_counts_by_code.get(top_failed_code, 0)
    top_failed_name = course_map.get(top_failed_code, top_failed_code)

    # 1. Summary KPI Strip
    if total_failed > 0:
        tiles = ctk.CTkFrame(body, fg_color="transparent")
        tiles.pack(fill="x", pady=(0, 16))
        pct_of_batch = round(total_failed / len(all_students) * 100, 2) if all_students else 0
        spec = [
            (str(total_failed), "Total Failed Candidates", f"{pct_of_batch}% of total batch", T.RED),
            (str(single_count), "Single-Subject Backlogs", f"{round(single_count / total_failed * 100, 1) if total_failed else 0}% of failures", "#b45309"),
            (str(multi_count), "Multiple Backlogs (≥2)", f"{round(multi_count / total_failed * 100, 1) if total_failed else 0}% of failures", T.RED),
            (f"{top_failed_name[:24]} ({top_failed_count})" if top_failed_count > 0 else "None", "Highest Failure Subject", f"{top_failed_count} students with backlog", T.TEXT),
        ]
        w_tiles = []
        for val, title, sub, col in spec:
            tile = ctk.CTkFrame(tiles, fg_color=T.CANVAS_BG, border_width=1, border_color=T.BORDER, corner_radius=T.R_MD)
            ctk.CTkLabel(tile, text=val, font=F("brand", 20), text_color=col, anchor="w").pack(fill="x", padx=16, pady=(12, 0))
            ctk.CTkLabel(tile, text=title, font=F("ui7", 11), text_color=T.TEXT, anchor="w").pack(fill="x", padx=16, pady=(2, 0))
            ctk.CTkLabel(tile, text=sub, font=F("ui", 10), text_color=T.MUTED, anchor="w").pack(fill="x", padx=16, pady=(0, 12))
            w_tiles.append(tile)
        grid_equal(tiles, w_tiles, 4, gap=14, uniform="kpi")

    # Dropdown options:
    # 0: "All Failed Candidates (5)" (DEFAULT!)
    # Followed by subjects sorted with subjects having failures first!
    sorted_subjects = sorted(subjects, key=lambda s: len(failures.get(s["code"], [])), reverse=True)

    ALL_KEY = "__ALL__"
    labels = [f"All Failed Candidates ({total_failed})"]
    lookup_keys = [ALL_KEY]

    for s in sorted_subjects:
        c_code = s["code"]
        c_fail_count = len(failures.get(c_code, []))
        labels.append(f"{s['name']} ({c_code}) · {c_fail_count} failed")
        lookup_keys.append(c_code)

    wrap = ctk.CTkFrame(body, fg_color="transparent")
    wrap.pack(fill="x")

    # ---- left: subject-wise remedial / all failed candidates -------------------------
    left = Card(wrap)
    head = ctk.CTkFrame(left, fg_color="transparent")
    head.pack(fill="x", padx=20, pady=(20, 16))
    titles = ctk.CTkFrame(head, fg_color="transparent")
    titles.pack(side="left", fill="x", expand=True)
    title_lbl = ctk.CTkLabel(titles, text="Failed Students & Remedial Register", font=F("ui7", 14), text_color=T.TEXT, anchor="w")
    title_lbl.pack(anchor="w")
    count_lbl = ctk.CTkLabel(titles, text="Select a filter to view candidate records", font=F("ui", 11), text_color=T.TEXT, anchor="w")
    count_lbl.pack(anchor="w")

    # Columns when showing All Failed Candidates
    cols_all = [
        {"title": "Register Number", "w": 130, "flex": 1},
        {"title": "Student Name", "w": 150, "flex": 2},
        {"title": "Failed Subject(s)", "w": 220, "flex": 3},
        {"title": "Count", "w": 60, "flex": 0},
        {"title": "Total", "w": 65, "flex": 0},
        {"title": "Status", "w": 75, "flex": 0},
    ]

    # Columns when showing a single specific Subject
    cols_subject = [
        {"title": "Register Number", "w": 130, "flex": 1},
        {"title": "Student Name", "w": 160, "flex": 2},
        {"title": "Theory", "w": 70, "flex": 0},
        {"title": "Internal", "w": 70, "flex": 0},
        {"title": "Total", "w": 70, "flex": 0},
        {"title": "Status", "w": 75, "flex": 0},
    ]

    current_rows_data: list[dict] = []

    def on_click_left(row_idx: int):
        if 0 <= row_idx < len(current_rows_data):
            usn = current_rows_data[row_idx].get("usn")
            if usn in students_by_usn:
                open_student_dialog(shell, students_by_usn[usn], courses)

    table = DataTable(left, cols_all, max_height=520, pad_x=8, on_click=on_click_left, empty_text="No failed students found.")

    def refresh():
        idx = select.index()
        key = lookup_keys[idx]
        current_rows_data.clear()

        if key == ALL_KEY:
            # Show ALL failed candidates across all subjects
            title_lbl.configure(text="All Failed Candidates Register")
            count_lbl.configure(text=f"Showing all {total_failed} candidate{'' if total_failed == 1 else 's'} with failed subjects (click row for full card)")
            table.set_columns(cols_all)
            rows = []
            for s in failed_students:
                current_rows_data.append(s)
                f_codes = [c for c, sub in s.get("subjects", {}).items() if sub.get("status") == "FAIL"]
                f_names = [course_map.get(c, c) for c in f_codes]
                rows.append([
                    Txt(s["usn"], "mono6"),
                    Txt(s["name"], "ui7"),
                    WrapCell(", ".join(f_names) if f_names else "General Backlog"),
                    CountCell(len(f_codes) if f_codes else 1),
                    Txt(str(s.get("total") or "-"), "ui7"),
                    BadgeCell(s.get("result") or "FAIL", "fail"),
                ])
            table.set_rows(rows)
        else:
            # Show candidates who failed the selected subject
            subj_name = course_map.get(key, key)
            failed = failures.get(key, [])
            n = len(failed)
            title_lbl.configure(text="Subject Remedial Register")
            count_lbl.configure(text=f"{n} student{'' if n == 1 else 's'} failed in {subj_name} (click row for full card)")
            table.set_columns(cols_subject)
            rows = []
            for item in failed:
                current_rows_data.append(item)
                rows.append([
                    Txt(item["usn"], "mono6"),
                    Txt(item["name"], "ui7"),
                    Txt(str(item.get("theory") if item.get("theory") is not None else "-")),
                    Txt(str(item.get("internal") if item.get("internal") is not None else "-")),
                    Txt(str(item.get("total") if item.get("total") is not None else "-"), "ui7"),
                    BadgeCell(item.get("status") or "FAIL", "fail"),
                ])
            table.set_rows(rows)

    select = Select(head, labels, refresh, width=320, size=11)
    select.pack(side="right", anchor="n", padx=(10, 0))
    table.pack(fill="x", padx=20, pady=(0, 20))

    # ---- right: multiple subject backlogs -------------------------------------------------
    right = Card(wrap)
    head2 = ctk.CTkFrame(right, fg_color="transparent")
    head2.pack(fill="x", padx=20, pady=(20, 16))
    ctk.CTkLabel(head2, text="Multiple Subject Backlogs", font=F("ui7", 14), text_color=T.TEXT).pack(side="left")
    n_multi = len(data.get("multiple_failures", []))
    ctk.CTkLabel(head2, text=f"{n_multi} student{'' if n_multi == 1 else 's'} with ≥2 failed subjects", font=F("ui", 11), text_color=T.TEXT).pack(side="right")

    cols2 = [{"title": "Register Number", "w": 130, "flex": 1}, {"title": "Student Name", "w": 130, "flex": 1},
             {"title": "Count", "w": 70, "flex": 0}, {"title": "Failed Subjects", "w": 190, "flex": 2}]

    def on_click_right(row_idx: int):
        multis = data.get("multiple_failures", [])
        if 0 <= row_idx < len(multis):
            usn = multis[row_idx]["usn"]
            if usn in students_by_usn:
                open_student_dialog(shell, students_by_usn[usn], courses)

    t2 = DataTable(right, cols2, max_height=520, pad_x=10, on_click=on_click_right, empty_text="No multi-subject failures found in source data.")
    t2.pack(fill="x", padx=20, pady=(0, 20))
    t2.set_rows([[Txt(m["usn"], "ui7"), Txt(m["name"]), CountCell(m["count"]), WrapCell(", ".join(m["subjects"]))]
                 for m in data.get("multiple_failures", [])])

    grid_equal(wrap, [left, right], 2, gap=18, uniform="fail")
    refresh()
