"""
Core processing and analytics engine for Result Analyzer.
Extracts metadata, dynamic course catalogues, and student mark cards from tabulation PDFs,
and prepares synthesized view data for the native CustomTkinter UI and Excel export.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
import pandas as pd
import pymupdf

import sys

if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "output"

USN_RE = re.compile(r"\bU\d{2}[A-Z0-9]{1,6}\d{2}[A-Z0-9]{3,}\b", re.I)
NUMBER_RE = re.compile(r"\b\d{1,3}\b")


class AnalysisError(Exception):
    """Raised with a user-facing message when a PDF cannot be processed."""


def clean_name(value: str) -> str:
    value = re.sub(r"\s+", " ", value).strip(" -|:")
    return value.title() if value.isupper() else value


def clean_term_grade(val: str | None) -> str:
    if not val:
        return ""
    cleaned = str(val).replace("\r", " ").replace("\n", " ").strip()
    cleaned = re.sub(r"\s+M(\.C.*)?$", "", cleaned, flags=re.I).strip()
    if "(" in cleaned and not cleaned.endswith(")"):
        cleaned += ")"
    return cleaned


def normalize_status(value: str) -> str:
    val = value.strip().upper()
    return {"P": "PASS", "F": "FAIL", "A": "ABSENT"}.get(val, val)


def _extract_usn_year(usn: str) -> str | None:
    if not usn:
        return None
    # Standard BU format: U03LX23S0001 (batch year is 23)
    m = re.search(r"^U\d{2}[A-Za-z]+(\d{2})[A-Za-z]\d+$", usn)
    if m:
        return m.group(1)
    # Generic format: U18BC21S001
    m = re.search(r"U\d{2}[A-Za-z]{1,4}(\d{2})", usn)
    if m:
        return m.group(1)
    # Prefix year format: 21BCA001
    m = re.search(r"^(\d{2})[A-Za-z]+", usn)
    if m:
        return m.group(1)
    # Embedded 2-digit batch year: 22BCO101
    m = re.search(r"\b(\d{2})[A-Za-z]{2,}\d+\b", usn)
    if m:
        return m.group(1)
    return None


def _tag_year_cohorts(records: list[dict]) -> None:
    years = Counter()
    for r in records:
        yr = _extract_usn_year(r.get("usn", ""))
        if yr:
            years[yr] += 1
    most_common_year = years.most_common(1)[0][0] if years else None

    for r in records:
        yr = _extract_usn_year(r.get("usn", ""))
        if not most_common_year or (yr and yr == most_common_year):
            r["year_type"] = "Current Year"
        else:
            r["year_type"] = "Backlog / Repeater"


def _parse_format2(pages: list[str], pdf_path: str | Path) -> tuple[dict, list[str]]:
    """Parse UUCMS / NEP Tabulation Ledger format with USN: candidate blocks."""
    warnings: list[str] = []

    # 1. Parse Metadata
    p1 = pages[0]
    prog_m = re.search(r"Program:\s*(.*?)(?=\n\s*Semester:)", p1, re.DOTALL)
    sem_m = re.search(r"Semester:\s*([A-Za-z0-9]+)", p1)
    exam_m = re.search(r"Exam Month:\s*\n?([A-Za-z0-9/]+)", p1)
    uni_m = re.search(r"^(.*University.*)$", p1, re.M)

    # Fallback to page footers if not found on page 1
    if len(pages) > 1:
        if not prog_m:
            prog_m = re.search(r"Program:\s*(.*?)(?=\n\s*Discipline|\n\s*Page|\n\s*Semester)", pages[1], re.DOTALL)
        if not sem_m:
            sem_m = re.search(r"Semester:\s*([A-Za-z0-9]+)", pages[1])
        if not exam_m:
            exam_m = re.search(r"Exam Month:\s*\n?([A-Za-z0-9/]+)", pages[1])
        if not uni_m:
            uni_m = re.search(r"^(.*University.*)$", pages[1], re.M)

    meta = {
        "university": uni_m.group(1).strip() if uni_m else "Bangalore University",
        "program": " ".join(prog_m.group(1).split()) if prog_m else "Degree Program",
        "semester": sem_m.group(1).strip() if sem_m else "",
        "exam_month": exam_m.group(1).strip() if exam_m else "",
    }

    # 2. Clean Pages and stitch student body (stripping headers & footers so multi-page student blocks unite)
    clean_pages = []
    for p in pages[1:]:
        t = re.sub(r"Page:\s*\d+\s+of\s+\d+.*", "", p, flags=re.DOTALL)
        t = re.sub(r"^\s*Candidate Details.*?Result\s*\n", "", t, flags=re.DOTALL)
        clean_pages.append(t)
    body = "\n".join(clean_pages)

    # 3. Split by Student USN Block
    blocks = re.split(r"(?=(?:USN|Reg(?:ister)?\.?\s*No|Roll\s*No)\s*[:\-]?\s*[A-Za-z0-9]+)", body, flags=re.I)
    student_blocks = [b.strip() for b in blocks if re.search(r"(?:USN|Reg(?:ister)?\.?\s*No|Roll\s*No)\s*[:\-]?\s*[A-Za-z0-9]+", b, re.I)]
    if not student_blocks:
        blocks = re.split(r"(?=USN:\s*[A-Za-z0-9]+)", body)
        student_blocks = [b.strip() for b in blocks if re.search(r"USN:\s*[A-Za-z0-9]+", b)]
    if not student_blocks:
        raise AnalysisError("No valid student tabulation records were identified in the PDF.")

    records = []
    seen_courses: dict[str, str] = {}

    for b in student_blocks:
        usn_m = re.search(r"(?:USN|Reg(?:ister)?\.?\s*(?:No|Num)?|Roll\s*No)\s*[:\-]?\s*([A-Za-z0-9]+)", b, re.I)
        if not usn_m:
            usn_m = USN_RE.search(b)
        if not usn_m:
            continue
        usn = usn_m.group(1).upper() if usn_m.lastindex else usn_m.group(0).upper()

        name_m = re.search(r"(?:Student\s*Name|Candidate\s*Name|Name)\s*[:\-]?\s*(.*?)(?=\n\s*(?:Father|Mother|Parent|SGPA|CGPA|Result|Term|Class|Marks|Subject|\n\n))", b, re.DOTALL | re.I)
        name = clean_name(name_m.group(1)) if name_m else ""

        sgpa_m = re.search(r"SGPA\s*[:\-]?\s*([\d.]+|\-)", b, re.I)
        cgpa_m = re.search(r"CGPA\s*[:\-]?\s*([\d.]+|\-)", b, re.I)
        res_m = re.search(r"Result\s*[:\-]?\s*(PASS|FAIL|ABSENT|Pass|Fail|Absent)", b, re.I)
        grade_m = re.search(r"Term\s*Grade\s*[:\-]?\s*([^\n\r]+(?:\n\([^\n\r]+\))?)", b, re.I)

        sgpa = float(sgpa_m.group(1)) if (sgpa_m and sgpa_m.group(1) != "-") else None
        cgpa = float(cgpa_m.group(1)) if (cgpa_m and cgpa_m.group(1) != "-") else None
        term_grade = clean_term_grade(grade_m.group(1)) if (grade_m and grade_m.group(1).strip() != "-") else None

        m_card = re.search(r"(?:Marks\s*card\s*\n?No|M\.?C\.?\s*No|Sl\.?\s*No)\s*[:\-]?\s*([A-Za-z0-9]+)", b, re.I)
        if m_card:
            subj_part = b[:m_card.start()]
            tot_part = b[m_card.end():]
        else:
            tot_idx = b.rfind("\nTotal\n")
            subj_part = b[:tot_idx] if tot_idx != -1 else b
            tot_part = b[tot_idx:] if tot_idx != -1 else ""

        lines = [l.strip() for l in subj_part.split("\n") if l.strip()]
        plus_idx = [i for i, l in enumerate(lines) if re.match(r"^\s*([0-9.]+|[\-A-Za-z]+)\s*\+\s*([0-9.]+|[\-A-Za-z]+)\s*$", l)]

        subjects_data = {}
        for i, p in enumerate(plus_idx):
            candidate_code = lines[p - 2]
            candidate_name = lines[p - 1]
            if re.search(r"^[A-Z0-9\s\-]+$", candidate_name) and " " not in candidate_name and (" " in candidate_code or len(candidate_code) > len(candidate_name)):
                code = candidate_name
                name_sub = candidate_code
            else:
                code = candidate_code
                name_sub = candidate_name

            if code not in seen_courses:
                seen_courses[code] = name_sub

            m_parts = re.match(r"^\s*([0-9.]+|[\-A-Za-z]+)\s*\+\s*([0-9.]+|[\-A-Za-z]+)\s*$", lines[p])
            cia_str = m_parts.group(1) if m_parts else ""
            see_str = m_parts.group(2) if m_parts else ""
            internal = int(float(cia_str)) if re.match(r"^\d+(\.\d+)?$", cia_str) else None
            theory = int(float(see_str)) if re.match(r"^\d+(\.\d+)?$", see_str) else None

            grace = int(lines[p + 1]) if (p + 1 < len(lines) and lines[p + 1].isdigit()) else 0
            max_tot = int(lines[p + 2]) if (p + 2 < len(lines) and lines[p + 2].isdigit()) else None
            tot_obt = int(lines[p + 3]) if (p + 3 < len(lines) and lines[p + 3].isdigit()) else None
            crs = int(lines[p + 4]) if (p + 4 < len(lines) and lines[p + 4].isdigit()) else None

            next_start = plus_idx[i + 1] - 2 if i + 1 < len(plus_idx) else len(lines)
            tail = lines[p + 5 : next_start]
            tail_str = " ".join(tail).lower()

            if "fail" in tail_str:
                status = "FAIL"
            elif "absent" in tail_str or "ab" in tail_str:
                status = "ABSENT"
            elif "pass" in tail_str:
                status = "PASS"
            else:
                status = "PASS" if (theory is not None or internal is not None) else "ABSENT"

            floats = [float(x) for x in tail if re.match(r"^\d+(\.\d+)?$", x)]
            gp = floats[0] if len(floats) >= 1 else None
            cp = floats[1] if len(floats) >= 2 else None

            subjects_data[code] = {
                "theory": theory,
                "internal": internal,
                "total": tot_obt,
                "status": status,
                "cr": crs,
                "gp": gp,
                "cp": cp,
            }

            if theory is not None and internal is not None and tot_obt is not None:
                if theory + internal != tot_obt:
                    warnings.append(f"{usn}: {code} theory + internal mismatch")

        # Parse total part
        tot_lines = [l.strip() for l in tot_part.split("\n") if l.strip()]
        tot_plus_idx = [i for i, l in enumerate(tot_lines) if re.match(r"^\s*[\d\-]+\s*\+\s*[\d\-]+\s*$", l)]
        grand_total = None
        max_total = None
        if tot_plus_idx:
            tp = tot_plus_idx[0]
            if tp + 2 < len(tot_lines) and tot_lines[tp + 2].isdigit():
                max_total = int(tot_lines[tp + 2])
            if tp + 3 < len(tot_lines) and tot_lines[tp + 3].isdigit():
                grand_total = int(tot_lines[tp + 3])

        if grand_total is None and subjects_data:
            grand_total = sum(s["total"] for s in subjects_data.values() if s.get("total") is not None)
        if max_total is None and subjects_data:
            max_total = sum(100 if s.get("cr", 4) == 4 else 50 for s in subjects_data.values())

        percentage = round(grand_total / max_total * 100, 2) if (grand_total is not None and max_total and max_total > 0) else None
        overall_result = res_m.group(1).upper() if res_m else (
            "PASS" if subjects_data and all(s["status"] == "PASS" for s in subjects_data.values()) else "FAIL"
        )

        records.append({
            "serial": str(len(records) + 1),
            "usn": usn,
            "name": name,
            "subjects": subjects_data,
            "total": grand_total,
            "max_total": max_total,
            "percentage": percentage,
            "result": overall_result,
            "sgpa": sgpa,
            "cgpa": cgpa,
            "grade": term_grade,
        })

    if not records:
        raise AnalysisError("No student records could be parsed from the PDF document.")

    courses = [{"sl_no": i + 1, "code": c, "name": n} for i, (c, n) in enumerate(seen_courses.items())]

    # Cohort segmentation (Current Year vs Backlog / Repeater)
    _tag_year_cohorts(records)

    return {
        "metadata": meta,
        "courses": courses,
        "records": records,
        "warnings": warnings,
        "filename": Path(pdf_path).name,
        "format_type": "UUCMS / NEP Tabulation Ledger",
    }, warnings


def parse_pdf_data(pdf_path: str | Path) -> tuple[dict, list[str]]:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise AnalysisError("The selected file could not be found.")
    if pdf_path.suffix.lower() != ".pdf":
        raise AnalysisError("Invalid file type. Please select a PDF document.")

    try:
        doc = pymupdf.open(str(pdf_path))
    except Exception as err:
        raise AnalysisError(f"Could not open PDF document: {err}")

    if len(doc) == 0:
        doc.close()
        raise AnalysisError("The selected PDF document contains no pages.")

    pages = [page.get_text("text") for page in doc]
    doc.close()

    full_text = "\n".join(pages)
    if not full_text.strip():
        raise AnalysisError("The PDF document contains no readable text.")

    # Multi-format detection with automated fallback:
    is_f2 = bool(re.search(r"Candidate Details", full_text, re.I) or re.search(r"USN:\s*[A-Za-z0-9]+", full_text))
    is_f1 = bool(re.search(r"Tabulation Register", full_text, re.I) or re.search(r"(?m)^\s*\d{4,5}\s*$", full_text))

    if is_f2 and not is_f1:
        strategies = [
            ("UUCMS / NEP Tabulation Ledger", lambda: _parse_format2(pages, pdf_path)),
            ("Legacy Tabulation Register", lambda: _parse_format1(pages, full_text, pdf_path)),
            ("Universal Tabular Sheet", lambda: _parse_format_universal(pages, full_text, pdf_path)),
        ]
    elif is_f1 and not is_f2:
        strategies = [
            ("Legacy Tabulation Register", lambda: _parse_format1(pages, full_text, pdf_path)),
            ("UUCMS / NEP Tabulation Ledger", lambda: _parse_format2(pages, pdf_path)),
            ("Universal Tabular Sheet", lambda: _parse_format_universal(pages, full_text, pdf_path)),
        ]
    else:
        strategies = [
            ("UUCMS / NEP Tabulation Ledger", lambda: _parse_format2(pages, pdf_path)),
            ("Legacy Tabulation Register", lambda: _parse_format1(pages, full_text, pdf_path)),
            ("Universal Tabular Sheet", lambda: _parse_format_universal(pages, full_text, pdf_path)),
        ]

    errors = []
    for fmt_name, parser in strategies:
        try:
            bundle, warnings = parser()
            if bundle and bundle.get("records"):
                return bundle, warnings
        except Exception as err:
            errors.append(f"[{fmt_name}] {err}")
            continue

    raise AnalysisError(f"Unable to extract student records from this PDF format.\nAttempted parsers:\n" + "\n".join(errors))


def _parse_format1(pages: list[str], full_text: str, pdf_path: str | Path) -> tuple[dict, list[str]]:
    """Parse legacy Bangalore University Tabulation Register (with Sl.No and serial student blocks)."""
    # 1. Parse Metadata from Page 1
    p1 = pages[0]
    prog_m = re.search(r"for\s+(.+?)(?:\s{2,}|$)", p1)
    sem_m = re.search(r"Semester\s*:\s*([A-Za-z0-9]+)", p1)
    uni_m = re.search(r"^(.*University.*)$", p1, re.M)
    exam_m = re.search(r"Exam Month\s*:\s*([A-Za-z0-9/]+)", p1)
    meta = {
        "university": uni_m.group(1).strip() if uni_m else "Bangalore University",
        "program": prog_m.group(1).strip() if prog_m else "Degree Program",
        "semester": sem_m.group(1).strip() if sem_m else "",
        "exam_month": exam_m.group(1).strip() if exam_m else "",
    }

    # 2. Parse Course Index from Page 1
    courses: list[dict] = []
    lines_p1 = [line.strip() for line in p1.split("\n")]
    in_table = False
    i = 0
    while i < len(lines_p1):
        s = lines_p1[i]
        if "Sl.No" in s or "SI.No" in s or "Sl. No" in s or "Course Code" in s:
            in_table = True
            i += 1
            while i < len(lines_p1) and lines_p1[i] in ("Course Code", "Course Name", ""):
                i += 1
            continue
        if in_table:
            if not s or "Printed Date" in s or "Page" in s:
                in_table = False
                i += 1
                continue
            m_single = re.match(r"^\s*(\d+)\s+([A-Z0-9\-]+)\s+(.+)$", s)
            if m_single:
                courses.append({
                    "sl_no": int(m_single.group(1)),
                    "code": m_single.group(2).strip(),
                    "name": m_single.group(3).strip()
                })
            elif re.match(r"^\d+$", s):
                sl_no = int(s)
                code = lines_p1[i + 1].strip() if i + 1 < len(lines_p1) else ""
                name = lines_p1[i + 2].strip() if i + 2 < len(lines_p1) else ""
                j = i + 3
                while j < len(lines_p1):
                    nxt = lines_p1[j].strip()
                    if re.match(r"^\d+$", nxt) or not nxt or "Printed" in nxt or "Page" in nxt:
                        break
                    if re.match(r"^[A-Z0-9\s,.\-&/()]+$", nxt) and len(nxt) > 1:
                        name += " " + nxt
                    else:
                        break
                    j += 1
                if code and name:
                    courses.append({"sl_no": sl_no, "code": code, "name": name.strip()})
        i += 1

    # 3. Parse Student Blocks
    student_matches = list(re.finditer(r"(?m)^\d{4,5}$", full_text))
    if not student_matches:
        raise AnalysisError("No valid student tabulation records were identified in the PDF.")

    records = []
    warnings = []
    course_code_set = {c["code"] for c in courses}

    for idx, match in enumerate(student_matches):
        start_pos = match.start()
        end_pos = student_matches[idx + 1].start() if idx + 1 < len(student_matches) else len(full_text)
        block = full_text[start_pos:end_pos]
        raw_lines = block.split("\n")
        serial = match.group(0)

        # USN
        usn_m = USN_RE.search(block)
        if not usn_m:
            continue
        usn = usn_m.group(0).upper()

        # Subject codes for this student block
        # Extract from Sub section first, respecting line splits
        student_codes: list[str] = []
        try:
            sub_idx = [i for i, l in enumerate(raw_lines) if l.strip() == "Sub"][0]
            total_usn_idx = [i for i in range(sub_idx + 1, len(raw_lines)) if raw_lines[i].strip() in ("Total", "USN")][0]
            sub_slice = [l.strip() for l in raw_lines[sub_idx + 1 : total_usn_idx] if l.strip()]
            li = 0
            while li < len(sub_slice):
                c = sub_slice[li]
                if c.endswith("-") and re.match(r"^[A-Z0-9]+-$", c) and li + 1 < len(sub_slice):
                    student_codes.append(c + sub_slice[li + 1])
                    li += 2
                else:
                    student_codes.append(c)
                    li += 1
        except Exception:
            student_codes = []

        # If sub block didn't capture all, regex search
        if not student_codes:
            for line in raw_lines:
                for c in re.findall(r"\b([A-Z0-9]+-[A-Z0-9\-]+)\b", line.strip()):
                    if c not in student_codes and (c in course_code_set or re.match(r"^[A-Z]+\d*-[A-Z0-9\-]+$", c)):
                        student_codes.append(c)

        n_subs = len(student_codes)

        # Student Name and Theory / Practical mark lines
        name = "Unknown"
        th_marks_lines: list[str] = []
        pr_marks_lines: list[str] = []
        try:
            th_idx = [i for i, l in enumerate(raw_lines) if l.strip() == "Th"][0]
            pr_idx = [i for i, l in enumerate(raw_lines) if l.strip() == "Pr"][0]
            end_pr_idx = [i for i in range(pr_idx + 1, len(raw_lines)) if any(raw_lines[i].strip().startswith(kw) for kw in ("Grace", "Cr.", "SGPA", "Total"))][0]

            th_section = raw_lines[th_idx + 1 : pr_idx]
            if th_section:
                cand = th_section[-1].strip()
                if len(cand) > 1 and not re.search(r"\d", cand) and cand not in ("Th", "Pr", "Grace", "Sub", "Total", "Pass", "Fail", "Absent"):
                    name = clean_name(cand)
                    th_marks_lines = th_section[:-1]
                else:
                    th_marks_lines = th_section

            pr_marks_lines = raw_lines[pr_idx + 1 : end_pr_idx]
        except Exception:
            pass

        # Fallback for student name if not found between Th and Pr
        if name == "Unknown":
            for line in raw_lines:
                cand = line.strip()
                if (re.match(r"^[A-Za-z\s.\-]+$", cand)
                        and len(cand) > 2
                        and cand not in ("Th", "Pr", "Grace", "Sub", "Total", "Pass", "Fail", "Absent", "Class", "Result")
                        and not re.match(r"^[A-Z]{1,2}$", cand)
                        and "University" not in cand
                        and "College" not in cand):
                    name = clean_name(cand)
                    break

        def _parse_token(t: str) -> tuple[int | None, int | None]:
            nums = re.findall(r"\d{1,3}", t)
            if len(nums) >= 2:
                return int(nums[0]), int(nums[1])
            if len(nums) == 1:
                return int(nums[0]), None
            return None, None

        # Subject Totals and Grand Total
        total_match = re.search(r"Result:\s*(?:PASS|FAIL|Pass|Fail)\nTotal\n(.*?)(?=Class|\nMax\. Total)", block, re.DOTALL)
        total_values = [float(l.strip()) for l in total_match.group(1).splitlines() if re.match(r"^\d+(\.\d+)?$", l.strip())] if total_match else []

        # Max marks
        max_match = re.search(r"Max\.\s*Total\n(.*?)(?=Term Grade|\nLetter Grade|\nResult)", block, re.DOTALL)
        max_values = [float(l.strip()) for l in max_match.group(1).splitlines() if re.match(r"^\d+(\.\d+)?$", l.strip())] if max_match else []

        grand_total = int(total_values[-1]) if total_values and total_values[-1].is_integer() else (total_values[-1] if total_values else None)
        max_total = int(max_values[-1]) if max_values and max_values[-1].is_integer() else (max_values[-1] if max_values else None)

        # Cr, GP, CP rows
        cr_m = re.search(r"Cr\.?\n(.*?)(?=\nSGPA|\nGP|\nCGPA|\nTotal)", block, re.DOTALL)
        cr_vals = [float(l.strip()) for l in cr_m.group(1).splitlines() if re.match(r"^\d+(\.\d+)?$", l.strip())] if cr_m else []

        gp_m = re.search(r"\nGP\n(.*?)(?=\nCGPA|\nCP|\nResult|\nTotal)", block, re.DOTALL)
        gp_vals = [float(l.strip()) for l in gp_m.group(1).splitlines() if re.match(r"^\d+(\.\d+)?$", l.strip())] if gp_m else []

        cp_m = re.search(r"\nCP\n(.*?)(?=\nResult|\nTotal)", block, re.DOTALL)
        cp_vals = [float(l.strip()) for l in cp_m.group(1).splitlines() if re.match(r"^\d+(\.\d+)?$", l.strip())] if cp_m else []

        # Subject Results / Statuses
        res_tail = block[block.rfind("M.C.No"):] if "M.C.No" in block else block
        subject_statuses = [normalize_status(w) for w in re.findall(r"\b(Pass|Fail|Absent|P|F|A)\b", res_tail, re.I)]

        # SGPA, CGPA, Term Grade, Overall Result
        sgpa_m = re.search(r"SGPA\s+([\d.]+)", block, re.I)
        cgpa_m = re.search(r"CGPA\s+([\d.]+)", block, re.I)
        grade_m = re.search(r"Term\s+Grade:\s*([^\n\r]+)", block, re.I)
        overall_res_m = re.search(r"Result:\s*(PASS|FAIL|Pass|Fail|ABSENT)", block, re.I)

        sgpa = float(sgpa_m.group(1)) if sgpa_m else None
        cgpa = float(cgpa_m.group(1)) if cgpa_m else None
        term_grade = clean_term_grade(grade_m.group(1)) if grade_m else None

        # Build Per-Subject Map
        subjects_data = {}
        for pos, code in enumerate(student_codes):
            th_t = th_marks_lines[pos].strip() if pos < len(th_marks_lines) else ""
            pr_t = pr_marks_lines[pos].strip() if pos < len(pr_marks_lines) else ""

            th_pair = _parse_token(th_t)
            pr_pair = _parse_token(pr_t)

            if th_pair != (None, None) and pr_pair == (None, None):
                pair = th_pair
            elif pr_pair != (None, None) and th_pair == (None, None):
                pair = pr_pair
            elif th_pair != (None, None) and pr_pair != (None, None):
                pair = (th_pair[0] + pr_pair[0], (th_pair[1] or 0) + (pr_pair[1] or 0))
            else:
                pair = (None, None)

            if len(student_codes) == 1:
                raw_sub_total = total_values[0] if total_values else None
            else:
                raw_sub_total = total_values[pos] if pos < len(total_values) - 1 else None
            sub_total = int(raw_sub_total) if raw_sub_total is not None and raw_sub_total.is_integer() else raw_sub_total

            sub_status = subject_statuses[pos] if pos < len(subject_statuses) else ("ABSENT" if pair == (None, None) else "PASS")
            sub_cr = int(cr_vals[pos]) if pos < len(cr_vals) and (len(cr_vals) == n_subs or pos < len(cr_vals) - 1) else None
            sub_gp = gp_vals[pos] if pos < len(gp_vals) else None
            sub_cp = cp_vals[pos] if pos < len(cp_vals) and (len(cp_vals) == n_subs or pos < len(cp_vals) - 1) else None

            subjects_data[code] = {
                "theory": pair[0],
                "internal": pair[1],
                "total": sub_total,
                "status": sub_status,
                "cr": sub_cr,
                "gp": sub_gp,
                "cp": sub_cp,
            }
            if pair[0] is not None and pair[1] is not None and sub_total is not None:
                if pair[0] + pair[1] != sub_total:
                    warnings.append(f"{usn}: {code} theory + internal mismatch")

        # Fallback if student_codes were empty
        if not subjects_data and total_values:
            for idx_c, c in enumerate(courses):
                th_t = th_marks_lines[idx_c].strip() if idx_c < len(th_marks_lines) else ""
                pr_t = pr_marks_lines[idx_c].strip() if idx_c < len(pr_marks_lines) else ""
                th_p = _parse_token(th_t)
                pr_p = _parse_token(pr_t)
                pair = th_p if th_p != (None, None) else pr_p
                sub_total = int(total_values[idx_c]) if idx_c < len(total_values) - 1 and total_values[idx_c].is_integer() else None
                status_val = subject_statuses[idx_c] if idx_c < len(subject_statuses) else "PASS"
                subjects_data[c["code"]] = {
                    "theory": pair[0],
                    "internal": pair[1],
                    "total": sub_total,
                    "status": status_val,
                }

        # Percentage
        percentage = None
        if grand_total is not None and max_total and max_total > 0:
            percentage = round(grand_total / max_total * 100, 2)

        overall_result = overall_res_m.group(1).upper() if overall_res_m else (
            "ABSENT" if subjects_data and all(s["status"] == "ABSENT" for s in subjects_data.values()) else (
                "PASS" if subjects_data and all(s["status"] == "PASS" for s in subjects_data.values()) else "FAIL"
            )
        )

        records.append({
            "serial": serial,
            "usn": usn,
            "name": name,
            "subjects": subjects_data,
            "total": grand_total,
            "max_total": max_total,
            "percentage": percentage,
            "result": overall_result,
            "sgpa": sgpa,
            "cgpa": cgpa,
            "grade": term_grade,
        })

    if not records:
        raise AnalysisError("No student records could be parsed from the PDF document.")

    # Infer Course Catalog if courses table on page 1 was missing or incomplete
    if not courses:
        detected_codes = set()
        for r in records:
            detected_codes.update(r["subjects"].keys())
        courses = [{"sl_no": i + 1, "code": code, "name": code} for i, code in enumerate(sorted(detected_codes))]

    # Year Type Inference (Cohort segmentation)
    _tag_year_cohorts(records)

    return {
        "metadata": meta,
        "courses": courses,
        "records": records,
        "warnings": warnings,
        "filename": Path(pdf_path).name,
        "format_type": "Bangalore University Tabulation Register",
    }, warnings


def _parse_format_universal(pages: list[str], full_text: str, pdf_path: str | Path) -> tuple[dict, list[str]]:
    """Universal fallback parser for scorecards, student marks sheets, and generic tabular results."""
    warnings: list[str] = []

    # 1. Parse Metadata
    p1 = pages[0]
    prog_m = re.search(r"(?:Program|Course|Degree)\s*[:\-]?\s*(.*?)(?=\n\s*(?:Semester|Exam|Date)|$)", p1, re.I)
    sem_m = re.search(r"Semester\s*[:\-]?\s*([A-Za-z0-9]+)", p1, re.I)
    exam_m = re.search(r"Exam(?:ination)?\s*(?:Month|Date)?\s*[:\-]?\s*([A-Za-z0-9/]+)", p1, re.I)
    uni_m = re.search(r"^(.*(?:University|College|Institute).*)$", p1, re.M | re.I)

    meta = {
        "university": uni_m.group(1).strip() if uni_m else "University / Institution",
        "program": " ".join(prog_m.group(1).split()) if prog_m else "Degree Program",
        "semester": sem_m.group(1).strip() if sem_m else "",
        "exam_month": exam_m.group(1).strip() if exam_m else "",
    }

    # 2. Extract USNs across the document
    usn_matches = list(re.finditer(r"\b(U\d{2}[A-Z0-9]{6,14}|\d{2}[A-Z]{2,}\d{4,})\b", full_text, re.I))
    if not usn_matches:
        raise AnalysisError("No valid register numbers or student records found in the document.")

    records = []
    seen_courses: dict[str, str] = {}

    for i, m in enumerate(usn_matches):
        usn = m.group(1).upper()
        start = m.start()
        end = usn_matches[i + 1].start() if i + 1 < len(usn_matches) else len(full_text)
        block = full_text[start:end]

        name_m = re.search(r"(?:Name|Student|Candidate)\s*[:\-]?\s*([A-Za-z\s.]{3,35})(?=\n|$)", block, re.I)
        name = clean_name(name_m.group(1)) if name_m else ""

        sgpa_m = re.search(r"SGPA\s*[:\-]?\s*([\d.]+)", block, re.I)
        cgpa_m = re.search(r"CGPA\s*[:\-]?\s*([\d.]+)", block, re.I)
        sgpa = float(sgpa_m.group(1)) if sgpa_m else None
        cgpa = float(cgpa_m.group(1)) if cgpa_m else None

        res_m = re.search(r"(?:Result|Status)\s*[:\-]?\s*(PASS|FAIL|ABSENT)", block, re.I)
        overall_res = res_m.group(1).upper() if res_m else "PASS"

        subjects_data = {}
        for line in block.splitlines():
            m_sub = re.search(r"\b([A-Z0-9]{3,}-[A-Z0-9\-]+|[A-Z]{3,}\d+[A-Z0-9]*)\b", line)
            m_marks = re.findall(r"\b\d{1,3}\b", line)
            if m_sub and len(m_marks) >= 2:
                c_code = m_sub.group(1)
                sub_tot = int(m_marks[-1])
                sub_stat = "PASS" if "FAIL" not in line.upper() else "FAIL"
                seen_courses[c_code] = c_code
                subjects_data[c_code] = {
                    "theory": int(m_marks[0]) if len(m_marks) > 2 else None,
                    "internal": int(m_marks[1]) if len(m_marks) > 2 else None,
                    "total": sub_tot,
                    "status": sub_stat,
                }

        tot_m = re.search(r"(?:Total|Grand Total)\s*[:\-]?\s*(\d{2,4})", block, re.I)
        grand_total = int(tot_m.group(1)) if tot_m else (
            sum(s["total"] for s in subjects_data.values() if s.get("total") is not None) if subjects_data else None
        )
        max_total = len(subjects_data) * 100 if subjects_data else 700
        pct = round(grand_total / max_total * 100, 2) if grand_total and max_total else None

        records.append({
            "serial": str(len(records) + 1),
            "usn": usn,
            "name": name,
            "subjects": subjects_data,
            "total": grand_total,
            "max_total": max_total,
            "percentage": pct,
            "result": overall_res,
            "sgpa": sgpa,
            "cgpa": cgpa,
            "grade": None,
            "year_type": "Current Year",
        })

    if not records:
        raise AnalysisError("Could not extract student records with universal strategy.")

    courses = [{"sl_no": i + 1, "code": c, "name": n} for i, (c, n) in enumerate(seen_courses.items())]

    return {
        "metadata": meta,
        "courses": courses,
        "records": records,
        "warnings": warnings,
        "filename": Path(pdf_path).name,
        "format_type": "Universal Scorecard / Tabular Sheet",
    }, warnings


def build_view_data(parsed_bundle: dict) -> dict:
    raw_records = parsed_bundle["records"]
    courses = parsed_bundle["courses"]
    meta = parsed_bundle["metadata"]
    warnings = parsed_bundle.get("warnings", [])
    filename = parsed_bundle.get("filename", "")

    # Exclusively isolate Current Year regular students - repeaters are completely excluded from analysis
    current = [r for r in raw_records if r.get("year_type") == "Current Year"]
    if not current:
        current = raw_records

    records = current

    attended = sum(r["result"] in {"PASS", "FAIL"} for r in records)
    passed = sum(r["result"] == "PASS" for r in records)
    failed = sum(r["result"] == "FAIL" for r in records)
    absent = sum(r["result"] == "ABSENT" for r in records)

    # Subject Statistics (strictly Current Year)
    subject_stats_list = []
    for c in courses:
        code = c["code"]
        values = [r["subjects"].get(code) for r in records if code in r["subjects"]]
        numeric = [v["total"] for v in values if v and v.get("total") is not None]
        p_count = sum(bool(v and v.get("status") == "PASS") for v in values)
        f_count = sum(bool(v and v.get("status") == "FAIL") for v in values)
        a_count = sum(bool(v and v.get("status") == "ABSENT") for v in values)
        app = p_count + f_count
        subject_stats_list.append({
            "code": code,
            "name": c["name"],
            "appeared": app,
            "passed": p_count,
            "failed": f_count,
            "absent": a_count,
            "pass_percentage": round(p_count / app * 100, 2) if app else 0,
            "fail_percentage": round(f_count / app * 100, 2) if app else 0,
            "average": round(sum(numeric) / len(numeric), 2) if numeric else 0,
            "highest": max(numeric) if numeric else 0,
            "lowest": min(numeric) if numeric else 0,
        })

    # Subject Failures (strictly Current Year)
    subject_failures = {}
    for c in courses:
        code = c["code"]
        subject_failures[code] = [
            {"usn": r["usn"], "name": r["name"], **r["subjects"].get(code, {})}
            for r in records
            if r["subjects"].get(code, {}).get("status") == "FAIL"
        ]

    # Multiple Failures (strictly Current Year)
    multiple_failures = []
    for r in records:
        f_courses = [
            c["name"] for c in courses
            if r["subjects"].get(c["code"], {}).get("status") == "FAIL"
        ]
        if len(f_courses) > 1:
            multiple_failures.append({
                "usn": r["usn"],
                "name": r["name"],
                "count": len(f_courses),
                "subjects": f_courses,
            })

    # Toppers (strictly Current Year)
    eligible_toppers = sorted(
        [
            r for r in records
            if r["result"] == "PASS"
            and r["percentage"] is not None
            and all(r["subjects"].get(c["code"], {}).get("status") == "PASS" for c in courses if c["code"] in r["subjects"])
        ],
        key=lambda r: (r["total"] or 0, r["percentage"] or 0),
        reverse=True
    )
    overall_toppers = [
        {
            "usn": r["usn"],
            "name": r["name"],
            "total": r["total"],
            "percentage": r["percentage"],
            "max_total": r["max_total"]
        }
        for r in eligible_toppers[:10]
    ]

    # Subject-wise Toppers (strictly Current Year)
    subject_toppers = []
    for c in courses:
        code = c["code"]
        top_c = sorted(
            [r for r in records if r["subjects"].get(code, {}).get("status") == "PASS"],
            key=lambda r: r["subjects"].get(code, {}).get("total") or 0,
            reverse=True
        )[:3]
        subject_toppers.append({
            "code": code,
            "name": c["name"],
            "toppers": [
                {"usn": r["usn"], "name": r["name"], **r["subjects"][code]}
                for r in top_c
            ]
        })

    # Serial Students List sorted by Total (strictly Current Year)
    sorted_students = sorted(records, key=lambda x: x["total"] or 0, reverse=True)
    for idx, s in enumerate(sorted_students, 1):
        s["serial"] = str(idx)

    # Summaries (strictly Current Year students, count of repeaters completely removed)
    current_percentages = [r["percentage"] for r in records if r["percentage"] is not None]
    summary = {
        "total": len(records),
        "attended": attended,
        "passed": passed,
        "failed": failed,
        "absent": absent,
        "pass_percentage": round(passed / attended * 100, 2) if attended else 0,
        "fail_percentage": round(failed / attended * 100, 2) if attended else 0,
        "current_year": len(records),
        "backlog": 0,
    }
    current_summary = {
        "total": len(records),
        "attended": attended,
        "passed": passed,
        "failed": failed,
        "pass_percentage": round(passed / attended * 100, 2) if attended else 0,
        "average_percentage": round(sum(current_percentages) / len(current_percentages), 2) if current_percentages else 0,
    }

    return {
        "summary": summary,
        "current": current_summary,
        "subjects": subject_stats_list,
        "students": sorted_students,
        "subject_failures": subject_failures,
        "multiple_failures": multiple_failures,
        "toppers": overall_toppers,
        "subject_toppers": subject_toppers,
        "backlog_students": [],
        "warnings": warnings,
        "filename": filename,
        "format_type": parsed_bundle.get("format_type", "Standard Tabulation Register"),
        "metadata": meta,
        "courses": courses,
    }


def analyze_pdf_file(path: str | Path) -> dict:
    """Entry point used by UI shell: parses PDF and constructs full view data dictionary."""
    parsed_bundle, warnings = parse_pdf_data(path)
    return build_view_data(parsed_bundle)


def default_export_name(meta: dict | None = None) -> str:
    if meta:
        sem = meta.get("semester", "")
        sem_ord = {"1": "1st", "2": "2nd", "3": "3rd", "4": "4th", "5": "5th", "6": "6th", "7": "7th", "8": "8th",
                   "I": "1st", "II": "2nd", "III": "3rd", "IV": "4th", "V": "5th", "VI": "6th", "VII": "7th", "VIII": "8th"}.get(str(sem).strip().upper(), str(sem))
        prog_raw = meta.get("program", "")
        if "Computer" in prog_raw:
            prog = "BCA"
        elif "Science" in prog_raw:
            prog = "BSc"
        elif "Commerce" in prog_raw:
            prog = "BCom"
        elif "Business" in prog_raw:
            prog = "BBA"
        else:
            prog = re.sub(r"[^A-Za-z0-9]", "", prog_raw) or "Result"
        exam = meta.get("exam_month", "").replace("/", "").replace(" ", "")
        parts = [p for p in [f"{sem_ord}_Sem" if sem_ord else "", prog, exam, "Result_Analysis"] if p]
        if parts:
            return "_".join(parts) + ".xlsx"
    return f"student_result_analysis_{datetime.now():%Y%m%d_%H%M%S}.xlsx"


def export_excel_file(data: dict, path: str | Path) -> Path:
    """Generate comprehensive multi-sheet Excel report."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use result-analyzer's advanced excel_exporter
    try:
        from excel_exporter import export_pretty_excel
    except ImportError:
        from src.excel_exporter import export_pretty_excel

    # Prepare DataFrame matching excel_exporter expectations
    rows = []
    courses = data.get("courses", [])
    for s in data["students"]:
        row = {
            "Serial": s.get("serial", ""),
            "USN": s["usn"],
            "Name": s["name"],
            "SGPA": s.get("sgpa") or 0.0,
            "CGPA": s.get("cgpa") or 0.0,
            "Result": s["result"],
            "Term Grade": s.get("grade") or "",
            "Total Marks": s.get("total") or 0.0,
            "Max Total": s.get("max_total") or 700.0,
            "Num Subjects": len(s["subjects"]),
            "Year Type": s.get("year_type", "Current Year"),
        }
        for code, sub in s["subjects"].items():
            row[f"{code}_GP"] = sub.get("gp", 0.0)
            row[f"{code}_CP"] = sub.get("cp", 0.0)
            row[f"{code}_Cr"] = sub.get("cr", 0)
        rows.append(row)
    df = pd.DataFrame(rows)

    export_pretty_excel(str(path), data, df)
    return path
