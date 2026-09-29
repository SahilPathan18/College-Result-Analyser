"""
Backend module for Bangalore University Result Analyzer.
Handles PDF parsing and data extraction.
"""

import pymupdf
import re

# ════════════════════════════════════════════════════════════════
# SECTION 1: PDF PARSER
# ════════════════════════════════════════════════════════════════
#
# The PDF has this structure:
#   Page 1  → Course index table (Sl.No, Course Code, Course Name)
#   Page 2+ → Student result blocks, each containing:
#             Serial (00001), Subject codes, USN, Th marks,
#             Student Name, Pr marks, Grace, Cr, GP, CP,
#             SGPA, CGPA, Result, Term Grade, M.C.No
#
# Challenge: PyMuPDF extracts text line-by-line, and some data is
# split across lines (e.g., "BCA5-" on one line, "DSCT1" on next).
# ════════════════════════════════════════════════════════════════

class TabulationParser:
    """Extracts metadata, courses, and student records from a BU PDF."""

    def __init__(self):
        self.metadata = {}     # {program, semester, exam_month, university}
        self.courses = []      # [{sl_no, code, name}, ...]
        self.students = []     # [{serial, usn, name, sgpa, cgpa, ...}, ...]

    # ── Main entry point ──
    def parse(self, pdf_path):
        """Read the PDF and return all parsed data as a dict."""
        doc = pymupdf.open(pdf_path)

        # Extract raw text from every page
        pages = [(p.get_text("text")) for p in doc]
        doc.close()

        # Step 1: Parse header info from page 1
        self._parse_metadata(pages[0])
        # Step 2: Parse course table from page 1
        self._parse_course_index(pages[0])
        # Step 3: Parse all student blocks from all pages combined
        self._parse_students("\n".join(pages))

        return {"metadata": self.metadata, "courses": self.courses, "students": self.students}

    # ── Helper: Search for a value using regex, return match or None ──
    def _find(self, pattern, text, group=1):
        """Shorthand regex search. Returns matched group or None."""
        m = re.search(pattern, text)
        return m.group(group).strip() if m else None

    # ── Helper: Parse a float safely ──
    @staticmethod
    def _float(val, default=0.0):
        """Convert string to float, returning default on failure."""
        try:
            return float(val)
        except (ValueError, TypeError):
            return default

    # ── Helper: Find a label on its own line and return the next line's value ──
    def _find_next_line_value(self, lines, label):
        """If 'label' is alone on a line, return the next line's content."""
        for i, line in enumerate(lines):
            if line.strip() == label and i + 1 < len(lines):
                return lines[i + 1].strip()
        return None

    # ── Helper: Collect consecutive numeric values after a label line ──
    @staticmethod
    def _collect_values_after(lines, start_idx):
        """Starting from start_idx, collect consecutive numeric lines."""
        values = []
        i = start_idx
        while i < len(lines):
            val = lines[i].strip()
            if re.match(r'^[\d.]+$', val):
                values.append(val)
                i += 1
            else:
                break
        return values, i

    # ── Step 1: Extract metadata (university, program, semester, exam month) ──
    def _parse_metadata(self, text):
        """Pull header info from the first page."""
        for line in text.split('\n'):
            # University name: any line with "University" that isn't the tabulation header
            if 'University' in line and 'Tabulation' not in line:
                self.metadata['university'] = line.strip()

            # Program: "Tabulation Register for Bachelor of Computer Applications"
            if 'Tabulation Register' in line:
                # Use non-greedy match, stop at multiple spaces (before Semester info)
                prog = self._find(r'for\s+(.+?)(?:\s{2,}|$)', line)
                if prog:
                    self.metadata['program'] = prog

            # Semester: "Semester : V"
            if 'Semester' in line:
                sem = self._find(r'Semester\s*:\s*(\S+)', line)
                if sem:
                    self.metadata['semester'] = sem

            # Exam Month: "Exam Month : DEC/2025"
            if 'Exam Month' in line:
                em = self._find(r'Exam\s*Month\s*:\s*(\S+)', line)
                if em:
                    self.metadata['exam_month'] = em

    # ── Step 2: Extract course index table ──
    def _parse_course_index(self, text):
        """
        Parse the course table from page 1.
        The PDF puts each field on its own line:
            '1'          ← sl_no
            'BCA5-DSCP1' ← course code
            'DATA ANALYTICS LAB' ← course name (may span multiple lines)
        """
        lines = text.split('\n')
        self.courses = []
        in_table = False

        # First attempt: single-line format (sl_no code name on one line)
        for line in lines:
            s = line.strip()
            if 'Sl.No' in s or 'SI.No' in s or 'Sl. No' in s:
                in_table = True
                continue
            if in_table:
                m = re.match(r'^\s*(\d+)\s+(\S+)\s+(.+)$', s)
                if m:
                    self.courses.append({'sl_no': int(m.group(1)), 'code': m.group(2), 'name': m.group(3).strip()})
                elif s == '' or 'Printed Date' in s or 'Page' in s:
                    in_table = False

        # If single-line didn't work, try multi-line format
        if not self.courses:
            in_table = False
            i = 0
            while i < len(lines):
                s = lines[i].strip()
                # Detect table start
                if 'Sl.No' in s or 'SI.No' in s or 'Sl. No' in s:
                    in_table = True
                    i += 1
                    # Skip column headers like "Course Code", "Course Name"
                    while i < len(lines) and lines[i].strip() in ('Course Code', 'Course Name', ''):
                        i += 1
                    continue

                if in_table:
                    # Detect table end
                    if s == '' or 'Printed Date' in s or 'Page' in s:
                        in_table = False
                        i += 1
                        continue

                    # Each course: sl_no line, code line, name line(s)
                    if re.match(r'^\d+$', s):
                        sl_no = int(s)
                        code = lines[i + 1].strip() if i + 1 < len(lines) else ''
                        name = lines[i + 2].strip() if i + 2 < len(lines) else ''
                        # Course name might wrap to next line(s)
                        j = i + 3
                        while j < len(lines):
                            nxt = lines[j].strip()
                            # Stop at next number, blank, or page markers
                            if re.match(r'^\d+$', nxt) or nxt == '' or 'Printed' in nxt or 'Page' in nxt:
                                break
                            if re.match(r'^[A-Z\s,.\-]+$', nxt) and len(nxt) > 1:
                                name += ' ' + nxt
                            else:
                                break
                            j += 1
                        if code and name:
                            self.courses.append({'sl_no': sl_no, 'code': code, 'name': name.strip()})
                i += 1

    # ── Helper: Rejoin split course codes ──
    @staticmethod
    def _reassemble_lines(lines):
        """
        Fix split course codes: 'BCA5-' + 'DSCT1' → 'BCA5-DSCT1'
        The PDF sometimes puts the prefix and suffix on separate lines.
        """
        result = []
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            # If line is just a code prefix ending with '-', join it with next line
            if s.endswith('-') and re.match(r'^[A-Z0-9]+-$', s) and i + 1 < len(lines):
                result.append(s + lines[i + 1].strip())
                i += 2  # Skip the next line since we merged it
            else:
                result.append(lines[i])
                i += 1
        return result

    # ── Step 3: Find all student blocks and parse each one ──
    def _parse_students(self, full_text):
        """
        Split the full text into student blocks (one per serial number)
        and extract data from each block.
        """
        self.students = []
        lines = full_text.split('\n')

        # Pass 1: Find line positions of all serial numbers (e.g., "00001", "00002")
        serials = [(i, lines[i].strip()) for i in range(len(lines))
                   if re.match(r'^\d{4,5}$', lines[i].strip())]

        # Pass 2: Extract each student's block (from one serial to the next)
        for idx, (pos, serial) in enumerate(serials):
            # Block ends at the next serial's position, or 200 lines max
            end = serials[idx + 1][0] if idx + 1 < len(serials) else min(pos + 200, len(lines))
            student = self._extract_student(lines[pos:end], serial)
            if student.get('usn'):  # Only keep students we could identify
                self.students.append(student)

    # ── Parse a single student's data block ──
    def _extract_student(self, raw_lines, serial):
        """
        Given a block of lines for one student, extract all their data.
        Returns a dict with: serial, usn, name, subjects, sgpa, cgpa, etc.
        """
        # Start with empty student record
        student = {
            'serial': serial, 'usn': '', 'name': '', 'subjects': {},
            'sgpa': 0.0, 'cgpa': 0.0, 'result': '', 'class': '',
            'term_grade': '', 'mc_no': '', 'total_marks': 0, 'max_total': 0,
        }

        # Fix split lines (e.g., "BCA5-" + "DSCT1" → "BCA5-DSCT1")
        lines = self._reassemble_lines(raw_lines)
        text = '\n'.join(lines)

        # ── USN ──
        # Try "USN U03LX23S0001" on same line first
        usn = self._find(r'USN\s+([A-Z0-9]{10,15})', text)
        if usn:
            student['usn'] = usn
        else:
            # Try "USN" alone on a line, value on the next line
            val = self._find_next_line_value(lines, 'USN')
            if val and re.match(r'^[A-Z0-9]{10,15}$', val):
                student['usn'] = val

        # ── Student Name ──
        # In this PDF, the name appears AFTER the "Th" (theory marks) row,
        # mixed in between the mark values. It's the first alphabetic-only line
        # after "Th" and before "Pr" (practical marks).
        found_th = False
        for line in lines:
            s = line.strip()
            if re.match(r'^Th\b', s):
                found_th = True
                continue
            if re.match(r'^Pr\b', s):
                break  # Stop at practical marks
            if found_th and s and len(s) > 2:
                # Name = alphabetic chars, spaces, dots, hyphens only
                if (re.match(r'^[A-Za-z\s.\-]+$', s) and
                        s not in ('Th', 'Pr', 'Grace', 'Sub', 'Total', 'Pass', 'Fail') and
                        not re.match(r'^[A-Z]{1,2}$', s)):  # Skip letter grades like "F"
                    student['name'] = s
                    break

        # ── Subject Codes ──
        # After reassembly, codes look like "BCA5-DSCT1" (LETTERS+DIGITS-LETTERS+DIGITS)
        codes = []
        for line in lines:
            for code in re.findall(r'\b([A-Z0-9]+-[A-Z0-9]+)\b', line.strip()):
                if re.match(r'^[A-Z]+\d*-[A-Z]+\d*$', code) and code not in codes:
                    codes.append(code)

        # ── SGPA / CGPA ── (try same-line first, then next-line)
        for field, label in [('sgpa', 'SGPA'), ('cgpa', 'CGPA')]:
            val = self._find(rf'{label}\s+([0-9]+\.?\d*)', text)
            if val:
                student[field] = self._float(val)
            else:
                nxt = self._find_next_line_value(lines, label)
                if nxt:
                    student[field] = self._float(nxt)

        # ── Result ── ("Result: PASS" or "Result: FAIL")
        res = self._find(r'Result:\s*(PASS|FAIL|Pass|Fail)', text)
        if res:
            student['result'] = res.upper()
        else:
            res = self._find(r'\bResult\b\s+(Pass|Fail)', text)
            if res:
                student['result'] = res.upper()

        # ── Term Grade ── ("Term Grade: B+ (Good)")
        grade = self._find(r'Term\s+Grade:\s*([^\n\r]+)', text)
        if grade:
            grade = re.sub(r'\s*(Letter|Grade|M\.C).*', '', grade, flags=re.IGNORECASE).strip()
            student['term_grade'] = grade

        # ── M.C.No ── ("M.C.No MC0326067359")
        mc = self._find(r'M\.C\.No\s+(\S+)', text)
        if mc:
            student['mc_no'] = mc

        # ── Row-based data: Cr, GP, CP, Total, Max Total ──
        # Each label sits on its own line, followed by numeric values on next lines.
        # Example:   Cr.
        #            4
        #            4
        #            3   ← these are credit values per subject
        data_rows = {'Cr': [], 'GP': [], 'CP': [], 'Total': [], 'Max': []}
        i = 0
        while i < len(lines):
            s = lines[i].strip()
            if re.match(r'^Cr\.?$', s):
                data_rows['Cr'], i = self._collect_values_after(lines, i + 1)
            elif s == 'GP':
                data_rows['GP'], i = self._collect_values_after(lines, i + 1)
            elif s == 'CP':
                data_rows['CP'], i = self._collect_values_after(lines, i + 1)
            elif s == 'Total':
                data_rows['Total'], i = self._collect_values_after(lines, i + 1)
            elif 'Max. Total' in s or 'Max Total' in s:
                data_rows['Max'], i = self._collect_values_after(lines, i + 1)
            else:
                i += 1

        # ── Build per-subject data ──
        for idx, code in enumerate(codes):
            subj = {'code': code, 'cr': 0, 'gp': 0.0, 'cp': 0.0, 'result': ''}
            if idx < len(data_rows['Cr']):
                subj['cr'] = int(self._float(data_rows['Cr'][idx]))
            if idx < len(data_rows['GP']):
                subj['gp'] = self._float(data_rows['GP'][idx])
            if idx < len(data_rows['CP']):
                subj['cp'] = self._float(data_rows['CP'][idx])
            student['subjects'][code] = subj

        # ── Aggregate totals (last value = combined total across all subjects) ──
        if data_rows['Total']:
            student['total_marks'] = self._float(data_rows['Total'][-1])
        if data_rows['Max']:
            student['max_total'] = self._float(data_rows['Max'][-1])

        return student
