"""
Excel Export Engine for College Result Analyser.
Generates executive-grade, beautifully formatted multi-sheet Excel reports
with KPI dashboards, zebra striping, conditional formatting, freeze panes,
and auto-fitted columns using openpyxl.
"""

import re
from datetime import datetime
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
import pandas as pd


def clean_term_grade(val) -> str:
    """Format Term Grade cleanly into single-line text without trailing PDF artifacts."""
    if val is None or pd.isna(val):
        return "-"
    cleaned = str(val).replace("\r", " ").replace("\n", " ").strip()
    cleaned = re.sub(r'\s+M(\.C.*)?$', '', cleaned, flags=re.IGNORECASE).strip()
    if "(" in cleaned and not cleaned.endswith(")"):
        cleaned += ")"
    return cleaned


def extract_letter_grade(val) -> str:
    """Extract standard letter grade (O, A+, A, B+, B, C, P, F) for analytics."""
    cleaned = clean_term_grade(val)
    m = re.match(r'^(O|A\+|A|B\+|B|C|P|F)(?:\s|\(|$)', cleaned, re.IGNORECASE)
    if m:
        return m.group(1).upper()
    if "FAIL" in cleaned.upper() or cleaned.startswith("-"):
        return "F"
    return cleaned


# ── Color Palette (Modern Executive Slate & Navy) ──
CLR_PRIMARY_NAVY = "1E3A8A"      # Main headers
CLR_PRIMARY_LIGHT = "EFF6FF"     # Soft metadata banner
CLR_INDIGO = "312E81"            # Secondary headers
CLR_ACCENT_BLUE = "2563EB"       # Accents & card banners
CLR_ALT_ROW = "F8FAFC"           # Zebra striping
CLR_WHITE = "FFFFFF"
CLR_TEXT_DARK = "0F172A"
CLR_TEXT_MUTED = "475569"
CLR_BORDER = "CBD5E1"            # Light clean border
CLR_BORDER_STRONG = "94A3B8"     # Stronger header border

# Status colors
CLR_PASS_BG = "DCFCE7"           # Soft emerald green
CLR_PASS_FG = "15803D"
CLR_FAIL_BG = "FEE2E2"           # Soft rose red
CLR_FAIL_FG = "B91C1C"
CLR_PROMOTED_BG = "FEF3C7"       # Soft amber
CLR_PROMOTED_FG = "B45309"

# Podium colors for top rankers
CLR_GOLD_BG = "FEF08A"
CLR_SILVER_BG = "E2E8F0"
CLR_BRONZE_BG = "FED7AA"


def _get_border(color=CLR_BORDER, style="thin"):
    side = Side(border_style=style, color=color)
    return Border(top=side, bottom=side, left=side, right=side)


def _get_header_border():
    thin = Side(border_style="thin", color=CLR_BORDER_STRONG)
    thick = Side(border_style="medium", color=CLR_PRIMARY_NAVY)
    return Border(top=thin, bottom=thick, left=thin, right=thin)


def _autofit_columns(ws, min_width=10, max_width=45):
    """Automatically adjust column widths to prevent text clipping."""
    for col in ws.columns:
        max_len = 0
        col_letter = get_column_letter(col[0].column)
        for cell in col:
            # Skip merged cells or multi-line header titles for width calc
            if cell.coordinate in ws.merged_cells:
                continue
            val_str = str(cell.value or "")
            if "\n" in val_str:
                val_str = max(val_str.split("\n"), key=len)
            max_len = max(max_len, len(val_str))
        ws.column_dimensions[col_letter].width = min(max(max_len + 4, min_width), max_width)


def _enable_gridlines(ws):
    """Ensure gridlines are visible even over filled cells."""
    ws.views.sheetView[0].showGridLines = True


def export_pretty_excel(filepath: str, data: dict, df: pd.DataFrame) -> None:
    """
    Build a comprehensive, beautifully styled multi-sheet Excel workbook.
    Sheets:
      1. Executive Summary (KPIs, Grade Distribution, Toppers Leaderboard)
      2. Student Master List (Full student marks & status with conditional formatting)
      3. Subject Analytics (Per-course pass rates, averages, failure metrics)
      4. Course Catalog (Official course syllabus index)
    """
    wb = openpyxl.Workbook()
    # Remove default sheet
    wb.remove(wb.active)

    metadata = data.get("metadata", {})
    courses = data.get("courses", [])

    # Ensure a working copy of student data
    students_df = df.copy() if df is not None else pd.DataFrame()
    if not students_df.empty:
        # Calculate Rank based on SGPA descending, then Total Marks
        if "SGPA" in students_df.columns:
            sort_cols = ["SGPA"]
            if "Total Marks" in students_df.columns:
                sort_cols.append("Total Marks")
            students_df = students_df.sort_values(by=sort_cols, ascending=False).reset_index(drop=True)
            students_df["Rank"] = range(1, len(students_df) + 1)

    # 1. Executive Summary Sheet
    _create_summary_sheet(wb, metadata, students_df, courses)

    # 2. Student Master List Sheet
    _create_students_sheet(wb, students_df, courses)

    # 3. Subject Analytics Sheet
    _create_subjects_sheet(wb, students_df, courses)

    # 4. Course Catalog Sheet
    _create_courses_sheet(wb, courses)

    # Save finalized workbook
    wb.save(filepath)


def _create_summary_sheet(wb, metadata, df, courses):
    ws = wb.create_sheet(title="Executive Summary")
    _enable_gridlines(ws)

    # ── Title Banner ──
    ws.merge_cells("A1:G1")
    title_cell = ws["A1"]
    title_cell.value = "COLLEGE RESULT ANALYZER - EXECUTIVE REPORT"
    title_cell.font = Font(name="Segoe UI", size=14, bold=True, color=CLR_WHITE)
    title_cell.fill = PatternFill(start_color=CLR_PRIMARY_NAVY, end_color=CLR_PRIMARY_NAVY, fill_type="solid")
    title_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 34

    # ── Metadata Banner ──
    ws.merge_cells("A2:G2")
    meta_cell = ws["A2"]
    univ = metadata.get("university", "Bangalore University")
    prog = metadata.get("program", "Undergraduate Program")
    sem = metadata.get("semester", "N/A")
    exam = metadata.get("exam_month", "N/A")
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    meta_cell.value = f"{univ}  |  {prog} (Sem: {sem})  |  Exam: {exam}  |  Exported: {now_str}"
    meta_cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_PRIMARY_NAVY)
    meta_cell.fill = PatternFill(start_color=CLR_PRIMARY_LIGHT, end_color=CLR_PRIMARY_LIGHT, fill_type="solid")
    meta_cell.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 22

    # Border below header banner
    thin_bottom = Border(bottom=Side(border_style="medium", color=CLR_PRIMARY_NAVY))
    for col_idx in range(1, 8):
        ws.cell(row=2, column=col_idx).border = thin_bottom

    # Calculations
    total_students = len(df)
    passed_students = len(df[df["Result"] == "PASS"]) if "Result" in df.columns else 0
    failed_students = total_students - passed_students
    pass_pct = (passed_students / total_students * 100) if total_students > 0 else 0.0

    valid_sgpa = df["SGPA"][df["SGPA"] > 0] if "SGPA" in df.columns else pd.Series(dtype=float)
    valid_cgpa = df["CGPA"][df["CGPA"] > 0] if "CGPA" in df.columns else pd.Series(dtype=float)

    avg_sgpa = valid_sgpa.mean() if not valid_sgpa.empty else 0.0
    max_sgpa = valid_sgpa.max() if not valid_sgpa.empty else 0.0
    min_sgpa = valid_sgpa.min() if not valid_sgpa.empty else 0.0
    avg_cgpa = valid_cgpa.mean() if not valid_cgpa.empty else 0.0

    # ── Section 1: KPI Metrics Table (Columns A-C) ──
    ws.merge_cells("A4:C4")
    kpi_hdr = ws["A4"]
    kpi_hdr.value = "KEY PERFORMANCE INDICATORS"
    kpi_hdr.font = Font(name="Segoe UI", size=10, bold=True, color=CLR_WHITE)
    kpi_hdr.fill = PatternFill(start_color=CLR_ACCENT_BLUE, end_color=CLR_ACCENT_BLUE, fill_type="solid")
    kpi_hdr.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[4].height = 22

    kpis = [
        ("Total Candidates", total_students, "#,##0"),
        ("Candidates Passed", passed_students, "#,##0"),
        ("Candidates Failed", failed_students, "#,##0"),
        ("Overall Pass Rate", pass_pct / 100.0, "0.0%"),
        ("Class Average SGPA", avg_sgpa, "0.00"),
        ("Highest SGPA", max_sgpa, "0.00"),
        ("Lowest SGPA", min_sgpa, "0.00"),
        ("Class Average CGPA", avg_cgpa, "0.00"),
    ]

    for i, (label, val, fmt) in enumerate(kpis, start=5):
        ws.row_dimensions[i].height = 20
        # Label cell (Cols A-B merged)
        ws.merge_cells(start_row=i, start_column=1, end_row=i, end_column=2)
        lbl_cell = ws.cell(row=i, column=1, value=label)
        lbl_cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_TEXT_DARK)
        lbl_cell.fill = PatternFill(start_color=CLR_ALT_ROW if i % 2 == 0 else CLR_WHITE, fill_type="solid")
        lbl_cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
        lbl_cell.border = _get_border()
        ws.cell(row=i, column=2).border = _get_border()

        # Value cell (Col C)
        val_cell = ws.cell(row=i, column=3, value=val)
        val_cell.font = Font(name="Segoe UI", size=9.5, bold=True, color=CLR_PRIMARY_NAVY)
        val_cell.fill = PatternFill(start_color=CLR_ALT_ROW if i % 2 == 0 else CLR_WHITE, fill_type="solid")
        val_cell.alignment = Alignment(horizontal="right", vertical="center")
        val_cell.number_format = fmt
        val_cell.border = _get_border()

    # ── Section 2: Grade Distribution Table (Columns E-G) ──
    ws.merge_cells("E4:G4")
    grd_hdr = ws["E4"]
    grd_hdr.value = "GRADE FREQUENCY DISTRIBUTION"
    grd_hdr.font = Font(name="Segoe UI", size=10, bold=True, color=CLR_WHITE)
    grd_hdr.fill = PatternFill(start_color=CLR_INDIGO, end_color=CLR_INDIGO, fill_type="solid")
    grd_hdr.alignment = Alignment(horizontal="center", vertical="center")

    sub_hdrs = ["Grade", "Count", "Percentage"]
    for c_idx, h_text in enumerate(sub_hdrs, start=5):
        c = ws.cell(row=5, column=c_idx, value=h_text)
        c.font = Font(name="Segoe UI", size=8.5, bold=True, color=CLR_TEXT_DARK)
        c.fill = PatternFill(start_color=CLR_PRIMARY_LIGHT, fill_type="solid")
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = _get_border()
    ws.row_dimensions[5].height = 18

    # Grade counting with robust regex normalization
    standard_grades = ["O", "A+", "A", "B+", "B", "C", "P", "F"]
    if "Term Grade" in df.columns:
        grade_series = df["Term Grade"].apply(extract_letter_grade)
        grade_counts = grade_series.value_counts().to_dict()
    else:
        grade_counts = {}

    for g_idx, grade in enumerate(standard_grades, start=6):
        ws.row_dimensions[g_idx].height = 19
        cnt = grade_counts.get(grade, 0)
        pct = (cnt / total_students) if total_students > 0 else 0.0
        bg = CLR_ALT_ROW if g_idx % 2 == 0 else CLR_WHITE

        # Grade
        g_c = ws.cell(row=g_idx, column=5, value=grade)
        g_c.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_TEXT_DARK)
        g_c.alignment = Alignment(horizontal="center", vertical="center")
        g_c.fill = PatternFill(start_color=bg, fill_type="solid")
        g_c.border = _get_border()

        # Count
        cnt_c = ws.cell(row=g_idx, column=6, value=cnt)
        cnt_c.font = Font(name="Segoe UI", size=9, color=CLR_TEXT_DARK)
        cnt_c.alignment = Alignment(horizontal="right", vertical="center")
        cnt_c.fill = PatternFill(start_color=bg, fill_type="solid")
        cnt_c.number_format = "#,##0"
        cnt_c.border = _get_border()

        # Percent
        pct_c = ws.cell(row=g_idx, column=7, value=pct)
        pct_c.font = Font(name="Segoe UI", size=9, color=CLR_TEXT_MUTED)
        pct_c.alignment = Alignment(horizontal="right", vertical="center")
        pct_c.fill = PatternFill(start_color=bg, fill_type="solid")
        pct_c.number_format = "0.0%"
        pct_c.border = _get_border()

    # ── Section 3: Toppers Leaderboard (Top 10) ──
    top_start_row = 15
    ws.merge_cells(f"A{top_start_row}:G{top_start_row}")
    top_hdr = ws[f"A{top_start_row}"]
    top_hdr.value = "SEMESTER TOPPERS & RANK HOLDERS (TOP 10)"
    top_hdr.font = Font(name="Segoe UI", size=10, bold=True, color=CLR_WHITE)
    top_hdr.fill = PatternFill(start_color=CLR_PRIMARY_NAVY, end_color=CLR_PRIMARY_NAVY, fill_type="solid")
    top_hdr.alignment = Alignment(horizontal="left", vertical="center", indent=1)
    ws.row_dimensions[top_start_row].height = 24

    top_cols = ["Rank", "Serial", "USN", "Student Name", "Result", "Grade", "SGPA"]
    sub_row = top_start_row + 1
    ws.row_dimensions[sub_row].height = 20
    for idx, col_name in enumerate(top_cols, start=1):
        c = ws.cell(row=sub_row, column=idx, value=col_name)
        c.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_TEXT_DARK)
        c.fill = PatternFill(start_color=CLR_PRIMARY_LIGHT, fill_type="solid")
        c.alignment = Alignment(horizontal="center" if idx != 4 else "left", vertical="center")
        c.border = _get_header_border()

    toppers_df = df.head(10) if not df.empty else pd.DataFrame()
    for t_idx, row in toppers_df.iterrows():
        curr_row = sub_row + 1 + t_idx
        ws.row_dimensions[curr_row].height = 20
        rank_num = t_idx + 1

        # Subtle podium shading for top 3
        if rank_num == 1:
            row_bg = CLR_GOLD_BG
        elif rank_num == 2:
            row_bg = CLR_SILVER_BG
        elif rank_num == 3:
            row_bg = CLR_BRONZE_BG
        else:
            row_bg = CLR_ALT_ROW if curr_row % 2 == 0 else CLR_WHITE

        values = [
            f"#{rank_num}",
            str(row.get("Serial", "")),
            str(row.get("USN", "")),
            str(row.get("Name", "")),
            str(row.get("Result", "")),
            clean_term_grade(row.get("Term Grade", "")),
            float(row.get("SGPA", 0.0)),
        ]

        for col_idx, val in enumerate(values, start=1):
            cell = ws.cell(row=curr_row, column=col_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9, bold=(rank_num <= 3 or col_idx == 7))
            cell.fill = PatternFill(start_color=row_bg, fill_type="solid")
            cell.border = _get_border()

            if col_idx == 4:
                cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            elif col_idx == 7:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "0.00"
            else:
                cell.alignment = Alignment(horizontal="center", vertical="center")

    _autofit_columns(ws, min_width=12, max_width=35)


def _create_students_sheet(wb, df, courses):
    ws = wb.create_sheet(title="Student Master List")
    _enable_gridlines(ws)

    if df.empty:
        ws.append(["No student data available"])
        return

    # Select and order columns cleanly
    core_cols = ["Rank", "Serial", "USN", "Name", "Result", "Term Grade", "SGPA", "CGPA", "Total Marks", "Max Total"]
    available_core = [c for c in core_cols if c in df.columns]

    # Include subject columns (GP and CP)
    subject_cols = [c for c in df.columns if c.endswith("_GP") or c.endswith("_CP") or c.endswith("_Cr")]
    final_cols = available_core + subject_cols

    # Add header row
    ws.append(final_cols)
    ws.row_dimensions[1].height = 26

    # Style header row
    for col_idx in range(1, len(final_cols) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(name="Segoe UI", size=9.5, bold=True, color=CLR_WHITE)
        cell.fill = PatternFill(start_color=CLR_PRIMARY_NAVY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = _get_header_border()

    # Append data rows
    for r_idx, (_, row) in enumerate(df[final_cols].iterrows(), start=2):
        ws.row_dimensions[r_idx].height = 20
        is_alt = (r_idx % 2 == 0)
        row_bg = CLR_ALT_ROW if is_alt else CLR_WHITE

        res_val = str(row.get("Result", "")).upper()

        for c_idx, col_name in enumerate(final_cols, start=1):
            val = row[col_name]
            if col_name == "Term Grade":
                val = clean_term_grade(val)
            elif pd.isna(val):
                val = ""

            cell = ws.cell(row=r_idx, column=c_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9, color=CLR_TEXT_DARK)
            cell.fill = PatternFill(start_color=row_bg, fill_type="solid")
            cell.border = _get_border()

            # Alignments & Number formats
            if col_name in ["Rank", "Serial", "USN", "Term Grade"]:
                cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_name == "Name":
                cell.alignment = Alignment(horizontal="left", vertical="center", indent=1)
            elif col_name in ["SGPA", "CGPA"]:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "0.00"
            elif col_name in ["Total Marks", "Max Total"] or col_name.endswith("_CP"):
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "#,##0"
            elif col_name.endswith("_GP") or col_name.endswith("_Cr"):
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = "0.0"
            elif col_name == "Result":
                cell.alignment = Alignment(horizontal="center", vertical="center")
                # Highlight PASS vs FAIL
                if res_val == "PASS":
                    cell.fill = PatternFill(start_color=CLR_PASS_BG, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_PASS_FG)
                elif "FAIL" in res_val:
                    cell.fill = PatternFill(start_color=CLR_FAIL_BG, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_FAIL_FG)
                elif "PROMOTED" in res_val:
                    cell.fill = PatternFill(start_color=CLR_PROMOTED_BG, fill_type="solid")
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_PROMOTED_FG)

    # Freeze header row & apply Excel AutoFilter
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _autofit_columns(ws, min_width=10, max_width=32)


def _create_subjects_sheet(wb, df, courses):
    ws = wb.create_sheet(title="Subject Performance")
    _enable_gridlines(ws)

    headers = [
        "Course Code", "Course Name", "Total Appeared",
        "Passed", "Failed", "Pass Rate", "Average GP", "Max GP"
    ]
    ws.append(headers)
    ws.row_dimensions[1].height = 26

    # Style Header
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(name="Segoe UI", size=9.5, bold=True, color=CLR_WHITE)
        cell.fill = PatternFill(start_color=CLR_INDIGO, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _get_header_border()

    # Match courses with per-subject GP columns
    course_name_map = {c.get("code", ""): c.get("name", "") for c in courses}
    gp_cols = [c for c in df.columns if c.endswith("_GP")] if not df.empty else []

    row_num = 2
    for col in gp_cols:
        code = col.replace("_GP", "")
        name = course_name_map.get(code, "Course " + code)
        series = df[col]
        appeared = len(series[series > 0])
        passed = len(series[series >= 4.0]) # Standard BU passing GP threshold
        failed = appeared - passed
        pass_rate = (passed / appeared) if appeared > 0 else 0.0
        avg_gp = series[series > 0].mean() if appeared > 0 else 0.0
        max_gp = series.max() if appeared > 0 else 0.0

        is_alt = (row_num % 2 == 0)
        row_bg = CLR_ALT_ROW if is_alt else CLR_WHITE
        ws.row_dimensions[row_num].height = 20

        vals = [
            (code, "center", "@"),
            (name, "left", "@"),
            (appeared, "right", "#,##0"),
            (passed, "right", "#,##0"),
            (failed, "right", "#,##0"),
            (pass_rate, "right", "0.0%"),
            (avg_gp, "right", "0.00"),
            (max_gp, "right", "0.00"),
        ]

        for c_idx, (val, align, fmt) in enumerate(vals, start=1):
            cell = ws.cell(row=row_num, column=c_idx, value=val)
            cell.font = Font(name="Segoe UI", size=9, color=CLR_TEXT_DARK)
            cell.fill = PatternFill(start_color=row_bg, fill_type="solid")
            cell.border = _get_border()
            cell.alignment = Alignment(horizontal=align, vertical="center", indent=(1 if align == "left" else 0))
            cell.number_format = fmt

            # Soft color on pass rate
            if c_idx == 6:
                if pass_rate >= 0.8:
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_PASS_FG)
                elif pass_rate < 0.5:
                    cell.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_FAIL_FG)

        row_num += 1

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    _autofit_columns(ws, min_width=12, max_width=40)


def _create_courses_sheet(wb, courses):
    ws = wb.create_sheet(title="Course Catalog")
    _enable_gridlines(ws)

    headers = ["Sl. No", "Course Code", "Course Name"]
    ws.append(headers)
    ws.row_dimensions[1].height = 26

    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = Font(name="Segoe UI", size=9.5, bold=True, color=CLR_WHITE)
        cell.fill = PatternFill(start_color=CLR_PRIMARY_NAVY, fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = _get_header_border()

    for idx, c in enumerate(courses, start=1):
        row_idx = idx + 1
        ws.row_dimensions[row_idx].height = 20
        row_bg = CLR_ALT_ROW if row_idx % 2 == 0 else CLR_WHITE

        c1 = ws.cell(row=row_idx, column=1, value=c.get("sl_no", idx))
        c1.alignment = Alignment(horizontal="center", vertical="center")

        c2 = ws.cell(row=row_idx, column=2, value=c.get("code", ""))
        c2.alignment = Alignment(horizontal="center", vertical="center")
        c2.font = Font(name="Segoe UI", size=9, bold=True, color=CLR_PRIMARY_NAVY)

        c3 = ws.cell(row=row_idx, column=3, value=c.get("name", ""))
        c3.alignment = Alignment(horizontal="left", vertical="center", indent=1)

        for cell in [c1, c2, c3]:
            cell.fill = PatternFill(start_color=row_bg, fill_type="solid")
            cell.border = _get_border()
            if cell != c2:
                cell.font = Font(name="Segoe UI", size=9, color=CLR_TEXT_DARK)

    ws.freeze_panes = "A2"
    _autofit_columns(ws, min_width=12, max_width=50)
