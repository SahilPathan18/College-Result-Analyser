"""
Frontend module for Bangalore University Result Analyzer.
Handles the GUI and data visualization.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk                      # Modern themed tkinter widgets
import matplotlib.pyplot as plt                   # Charts and graphs
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg  # Embed plots in tkinter
import numpy as np                                # Numeric utilities
import pandas as pd                               # DataFrames for tabular data
import os                                         # File path utilities

from backend import TabulationParser
try:
    from excel_exporter import export_pretty_excel
except ImportError:
    from src.excel_exporter import export_pretty_excel


# ──────────────── GLOBAL CONFIG ────────────────
plt.style.use('dark_background')       # Dark charts to match our dark UI
ctk.set_appearance_mode("Dark")        # Force dark mode for CustomTkinter
ctk.set_default_color_theme("blue")    # Blue accent theme

# ════════════════════════════════════════════════════════════════
# SECTION 2: GUI APPLICATION
# ════════════════════════════════════════════════════════════════
#
# Built with CustomTkinter (dark-themed tkinter wrapper).
# Layout:
#   ┌──────────┬──────────────────────────────┐
#   │ Sidebar  │  Main Content Area           │
#   │ (nav)    │  (scrollable, shows views)   │
#   └──────────┴──────────────────────────────┘
#
# Views: Dashboard | Students | Subjects | Analytics
# ════════════════════════════════════════════════════════════════

# Color palette used throughout the app
COLORS = {
    'bg_dark': '#1a1a2e',    'bg_card': '#16213e',
    'accent_1': '#0f3460',   'accent_2': '#e94560',
    'success': '#2ecc71',    'warning': '#f39c12',
    'danger': '#e74c3c',     'info': '#3498db',
    'text': '#ecf0f1',       'text_dim': '#95a5a6',
    'gold': '#f1c40f',       'silver': '#bdc3c7',
    'bronze': '#cd6839',     'purple': '#9b59b6',
}


class ResultAnalyzerApp(ctk.CTk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("📊 Bangalore University Result Analyzer")
        self.geometry("1280x850")
        self.minsize(1000, 700)

        # Core state
        self.parser = TabulationParser()
        self.data = None         # Raw parsed data dict
        self.df = None           # Pandas DataFrame of students
        self.active_figs = []    # Track matplotlib figures for cleanup

        # 2-column layout: sidebar (col 0) + main area (col 1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self._build_sidebar()
        self._build_main_area()

    # ──────────────── HELPER: Create a chart inside a card ────────────────
    def _make_chart(self, parent, figsize=(5, 3.5)):
        """Create a matplotlib figure + axes with our dark theme. Returns (fig, ax)."""
        fig, ax = plt.subplots(figsize=figsize, facecolor='#0d1117')
        ax.set_facecolor('#0d1117')
        self.active_figs.append(fig)  # Track for cleanup
        return fig, ax

    def _embed_chart(self, fig, parent):
        """Embed a matplotlib figure into a CTk card frame."""
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=COLORS['bg_card'])
        canvas = FigureCanvasTkAgg(fig, master=card)
        canvas.draw()
        canvas.get_tk_widget().pack(padx=10, pady=10, fill="both", expand=True)
        return card

    # ──────────────── HELPER: Create a stat card ────────────────
    def _make_card(self, parent, icon, value, title, color):
        """Create a single summary stat card (icon + big number + label)."""
        card = ctk.CTkFrame(parent, corner_radius=12, fg_color=COLORS['bg_card'])
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(padx=15, pady=15, fill="both", expand=True)
        ctk.CTkLabel(inner, text=icon, font=ctk.CTkFont(size=24)).pack(anchor="w")
        ctk.CTkLabel(inner, text=value, font=ctk.CTkFont(size=28, weight="bold"),
                     text_color=color).pack(anchor="w", pady=(5, 2))
        ctk.CTkLabel(inner, text=title, font=ctk.CTkFont(size=12),
                     text_color=COLORS['text_dim']).pack(anchor="w")
        return card

    # ════════════════ SIDEBAR ════════════════
    def _build_sidebar(self):
        """Build the left sidebar with logo, upload, nav, and export buttons."""
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0, fg_color=COLORS['bg_dark'])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(10, weight=1)  # Push bottom items down

        # Logo + title
        ctk.CTkLabel(self.sidebar, text="📊", font=ctk.CTkFont(size=40)
                     ).grid(row=0, column=0, padx=20, pady=(25, 5))
        ctk.CTkLabel(self.sidebar, text="Result Analyzer",
                     font=ctk.CTkFont(size=22, weight="bold"), text_color=COLORS['text']
                     ).grid(row=1, column=0, padx=20, pady=(0, 5))
        ctk.CTkLabel(self.sidebar, text="Bangalore University",
                     font=ctk.CTkFont(size=11), text_color=COLORS['text_dim']
                     ).grid(row=2, column=0, padx=20, pady=(0, 20))

        # Upload PDF button (always visible)
        ctk.CTkButton(
            self.sidebar, text="📁  Upload PDF", command=self.upload_pdf,
            font=ctk.CTkFont(size=14, weight="bold"), height=42, corner_radius=10,
            fg_color=COLORS['accent_2'], hover_color="#c73e54"
        ).grid(row=3, column=0, padx=20, pady=8, sticky="ew")

        # Navigation buttons (hidden until PDF is loaded)
        self.nav_buttons = {}
        for idx, (label, key) in enumerate([
            ("🏠  Dashboard", "dashboard"), ("👨‍🎓  Students", "students"),
            ("📚  Subjects", "subjects"), ("📈  Analytics", "analytics"),
        ]):
            btn = ctk.CTkButton(
                self.sidebar, text=label, command=lambda k=key: self.show_view(k),
                font=ctk.CTkFont(size=13), height=38, corner_radius=8,
                fg_color="transparent", hover_color=COLORS['accent_1'], anchor="w"
            )
            btn.grid(row=4 + idx, column=0, padx=15, pady=3, sticky="ew")
            btn.grid_remove()  # Hidden initially
            self.nav_buttons[key] = btn

        # Export button (hidden until PDF is loaded)
        self.export_btn = ctk.CTkButton(
            self.sidebar, text="💾  Export to Excel", command=self.export_excel,
            font=ctk.CTkFont(size=13), height=38, corner_radius=8,
            fg_color=COLORS['accent_1'], hover_color="#1a4a7a"
        )
        self.export_btn.grid(row=9, column=0, padx=15, pady=5, sticky="ew")
        self.export_btn.grid_remove()

        # Clear data button
        ctk.CTkButton(
            self.sidebar, text="🗑️  Clear Data", command=self.clear_data,
            font=ctk.CTkFont(size=12), height=32, corner_radius=8,
            fg_color="transparent", border_width=1, border_color=COLORS['text_dim'],
            text_color=COLORS['text_dim'], hover_color="#2c2c2c"
        ).grid(row=11, column=0, padx=15, pady=(5, 20), sticky="ew")

        # File name label (shows currently loaded PDF)
        self.file_label = ctk.CTkLabel(
            self.sidebar, text="", font=ctk.CTkFont(size=10),
            text_color=COLORS['text_dim'], wraplength=200
        )
        self.file_label.grid(row=12, column=0, padx=15, pady=(0, 10))

    # ════════════════ MAIN CONTENT AREA ════════════════
    def _build_main_area(self):
        """Build the main content area with welcome screen and scrollable content."""
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#0d1117")
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # Welcome screen (shown before PDF upload)
        self.welcome_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.welcome_frame.grid(row=0, column=0, sticky="nsew")
        self.welcome_frame.grid_rowconfigure(0, weight=1)
        self.welcome_frame.grid_columnconfigure(0, weight=1)

        inner = ctk.CTkFrame(self.welcome_frame, fg_color="transparent")
        inner.place(relx=0.5, rely=0.45, anchor="center")
        ctk.CTkLabel(inner, text="📊", font=ctk.CTkFont(size=60)).pack(pady=(0, 10))
        ctk.CTkLabel(inner, text="University Result Analyzer",
                     font=ctk.CTkFont(size=28, weight="bold"), text_color=COLORS['text']).pack(pady=(0, 8))
        ctk.CTkLabel(inner, text="Upload a Tabulation Register PDF to get started",
                     font=ctk.CTkFont(size=14), text_color=COLORS['text_dim']).pack(pady=(0, 25))
        ctk.CTkButton(inner, text="📁  Upload PDF", command=self.upload_pdf,
                      font=ctk.CTkFont(size=16, weight="bold"), height=48, width=220,
                      corner_radius=12, fg_color=COLORS['accent_2'], hover_color="#c73e54").pack()

        # Scrollable content frame (shown after PDF load, holds dashboard/students/etc.)
        self.content_frame = ctk.CTkScrollableFrame(self.main_frame, corner_radius=0, fg_color="#0d1117")

    # ════════════════ PDF UPLOAD & DATA LOADING ════════════════
    def upload_pdf(self):
        """Open file dialog, parse the PDF, and show the dashboard."""
        filename = filedialog.askopenfilename(
            title="Select Tabulation Register PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not filename:
            return
        try:
            # Parse PDF → structured data → DataFrame
            self.data = self.parser.parse(filename)
            self._build_dataframe()
            self.file_label.configure(text=f"📄 {os.path.basename(filename)}")

            # Show navigation buttons
            for btn in self.nav_buttons.values():
                btn.grid()
            self.export_btn.grid()

            # Switch from welcome screen to dashboard
            self.welcome_frame.grid_forget()
            self.content_frame.grid(row=0, column=0, sticky="nsew")
            self.show_view("dashboard")
        except Exception as e:
            messagebox.showerror("Parse Error", f"Failed to parse the PDF:\n\n{str(e)}")
            import traceback
            traceback.print_exc()

    def _build_dataframe(self):
        """Convert the list of student dicts into a pandas DataFrame."""
        rows = []
        for s in self.data['students']:
            row = {
                'Serial': s['serial'], 'USN': s['usn'], 'Name': s['name'],
                'SGPA': s['sgpa'], 'CGPA': s['cgpa'], 'Result': s['result'],
                'Term Grade': s['term_grade'], 'Total Marks': s['total_marks'],
                'Max Total': s['max_total'], 'Num Subjects': len(s['subjects']),
            }
            # Add per-subject columns (e.g., BCA5-DSCT1_GP, BCA5-DSCT1_CP)
            for code, subj in s['subjects'].items():
                row[f'{code}_GP'] = subj.get('gp', 0)
                row[f'{code}_CP'] = subj.get('cp', 0)
                row[f'{code}_Cr'] = subj.get('cr', 0)
            rows.append(row)
        self.df = pd.DataFrame(rows)

    # ════════════════ VIEW ROUTING ════════════════
    def show_view(self, view_name):
        """Switch between dashboard/students/subjects/analytics views."""
        # Highlight active nav button
        for key, btn in self.nav_buttons.items():
            btn.configure(fg_color=COLORS['accent_1'] if key == view_name else "transparent")

        # Clear old content and close old charts
        for fig in self.active_figs:
            plt.close(fig)
        self.active_figs.clear()
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Render the requested view
        views = {
            "dashboard": self._render_dashboard, "students": self._render_students,
            "subjects": self._render_subjects, "analytics": self._render_analytics,
        }
        views.get(view_name, lambda: None)()

    # ════════════════ VIEW 1: DASHBOARD ════════════════
    def _render_dashboard(self):
        """Main overview: stats cards, pie chart, histogram, grade bars, top performers."""
        df = self.df
        if df is None or df.empty:
            return

        # ── Header with metadata ──
        header = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 5))
        meta = self.data['metadata']
        ctk.CTkLabel(header, text=meta.get('university', 'Bangalore University'),
                     font=ctk.CTkFont(size=22, weight="bold"), text_color=COLORS['text']).pack(anchor="w")
        ctk.CTkLabel(header, text=f"{meta.get('program', '')}  •  Semester {meta.get('semester', '')}  •  {meta.get('exam_month', '')}",
                     font=ctk.CTkFont(size=13), text_color=COLORS['text_dim']).pack(anchor="w", pady=(2, 0))

        # ── Summary stat cards ──
        total = len(df)
        passed = len(df[df['Result'] == 'PASS'])
        failed = len(df[df['Result'] == 'FAIL'])
        pass_pct = (passed / total * 100) if total > 0 else 0
        avg_sgpa = df['SGPA'].mean() if not df['SGPA'].isna().all() else 0

        cards_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        cards_frame.pack(fill="x", padx=20, pady=15)
        cards_frame.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)

        for i, (icon, val, title, color) in enumerate([
            ("👨‍🎓", str(total), "Total Students", COLORS['info']),
            ("✅", str(passed), "Passed", COLORS['success']),
            ("❌", str(failed), "Failed", COLORS['danger']),
            ("📊", f"{pass_pct:.1f}%", "Pass %", COLORS['warning']),
            ("⭐", f"{avg_sgpa:.2f}", "Avg SGPA", COLORS['purple']),
        ]):
            self._make_card(cards_frame, icon, val, title, color).grid(
                row=0, column=i, padx=6, pady=5, sticky="nsew")

        # ── Charts Row: Pie (pass/fail) + Histogram (SGPA) ──
        charts_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        charts_row.pack(fill="x", padx=20, pady=10)
        charts_row.grid_columnconfigure((0, 1), weight=1)

        # Pie chart: Pass vs Fail
        fig1, ax1 = self._make_chart(charts_row)
        if total > 0:
            wedges, texts, autotexts = ax1.pie(
                [passed, failed], labels=[f'Passed ({passed})', f'Failed ({failed})'],
                colors=[COLORS['success'], COLORS['danger']],
                autopct='%1.1f%%', startangle=90, explode=(0.03, 0.03),
                textprops={'color': 'white', 'fontsize': 10},
                wedgeprops={'linewidth': 2, 'edgecolor': '#0d1117'})
            for t in autotexts:
                t.set_fontweight('bold')
        ax1.set_title("Pass / Fail Distribution", color='white', fontsize=13, pad=15, fontweight='bold')
        self._embed_chart(fig1, charts_row).grid(row=0, column=0, padx=6, pady=5, sticky="nsew")

        # Histogram: SGPA distribution
        fig2, ax2 = self._make_chart(charts_row)
        valid_sgpa = df['SGPA'][df['SGPA'] > 0]
        if not valid_sgpa.empty:
            ax2.hist(valid_sgpa, bins=np.arange(0, 10.5, 0.5), color=COLORS['info'],
                     edgecolor='#0d1117', alpha=0.85, rwidth=0.9)
            ax2.axvline(valid_sgpa.mean(), color=COLORS['accent_2'], linestyle='--',
                        linewidth=2, label=f'Mean: {valid_sgpa.mean():.2f}')
            ax2.legend(fontsize=9, loc='upper left')
        ax2.set_xlabel("SGPA", color='white', fontsize=10)
        ax2.set_ylabel("Students", color='white', fontsize=10)
        ax2.set_title("SGPA Distribution", color='white', fontsize=13, pad=15, fontweight='bold')
        self._embed_chart(fig2, charts_row).grid(row=0, column=1, padx=6, pady=5, sticky="nsew")

        # ── Bar chart: Term Grade distribution ──
        fig3, ax3 = self._make_chart(self.content_frame, figsize=(10, 3.5))
        grade_counts = df['Term Grade'].value_counts()
        if not grade_counts.empty:
            # Sort grades in a sensible order
            order = ['O (Outstanding)', 'A+ (Excellent)', 'A (Very Good)', 'B+ (Good)',
                     'B (Above Average)', 'C (Average)', 'P (Pass)', 'F (Fail)',
                     'O', 'A+', 'A', 'B+', 'B', 'C', 'P', 'F']
            sorted_g = [g for g in order if g in grade_counts.index]
            sorted_g += [g for g in grade_counts.index if g not in sorted_g]

            # Map grade letters to colors
            cmap = {'O': '#ffd700', 'A+': '#ffd700', 'A': '#c0c0c0', 'B+': '#cd7f32',
                    'B': '#3498db', 'C': '#9b59b6', 'P': '#f39c12', 'F': '#e74c3c'}
            gcolors = [next((c for k, c in cmap.items() if k in g), COLORS['info']) for g in sorted_g]
            counts = [grade_counts[g] for g in sorted_g]

            bars = ax3.bar(sorted_g, counts, color=gcolors, width=0.6, edgecolor='#0d1117')
            for bar, cnt in zip(bars, counts):
                ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                         str(cnt), ha='center', va='bottom', color='white', fontsize=10, fontweight='bold')
        ax3.set_title("Term Grade Distribution", color='white', fontsize=13, pad=15, fontweight='bold')
        ax3.tick_params(axis='x', rotation=25, labelsize=9)
        fig3.tight_layout()
        self._embed_chart(fig3, self.content_frame).pack(fill="x", padx=26, pady=10)

        # ── Top performers table ──
        top_frame = ctk.CTkFrame(self.content_frame, corner_radius=12, fg_color=COLORS['bg_card'])
        top_frame.pack(fill="x", padx=26, pady=10)
        ctk.CTkLabel(top_frame, text="🏆  Top Performers (by SGPA)",
                     font=ctk.CTkFont(size=15, weight="bold"), text_color=COLORS['gold']
                     ).pack(anchor="w", padx=15, pady=(12, 8))
        self._render_table(top_frame, df.nlargest(10, 'SGPA')[
            ['Serial', 'USN', 'Name', 'SGPA', 'CGPA', 'Result', 'Term Grade']], highlight_top=True)

    # ════════════════ VIEW 2: STUDENTS ════════════════
    def _render_students(self):
        """Searchable, filterable table of all students."""
        df = self.df
        if df is None or df.empty:
            return

        # Search bar
        search_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(15, 10))
        ctk.CTkLabel(search_frame, text="👨‍🎓  Student Results",
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=COLORS['text']).pack(side="left")
        self.search_var = ctk.StringVar()
        ctk.CTkEntry(search_frame, placeholder_text="🔍 Search by USN or Name...",
                     width=300, height=36, corner_radius=10, textvariable=self.search_var
                     ).pack(side="right", padx=5)
        self.search_var.trace_add("write", lambda *_: self._filter_students())

        # Filter buttons (All / PASS / FAIL)
        filter_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.result_filter = ctk.CTkSegmentedButton(filter_frame, values=["All", "PASS", "FAIL"],
                                                     command=self._filter_students)
        self.result_filter.set("All")
        self.result_filter.pack(side="left")
        self.student_count_label = ctk.CTkLabel(filter_frame, text=f"Showing {len(df)} students",
                                                 font=ctk.CTkFont(size=12), text_color=COLORS['text_dim'])
        self.student_count_label.pack(side="right")

        # Table
        self.student_table_frame = ctk.CTkFrame(self.content_frame, corner_radius=12, fg_color=COLORS['bg_card'])
        self.student_table_frame.pack(fill="both", expand=True, padx=20, pady=10)
        self._render_table(self.student_table_frame, df[['Serial', 'USN', 'Name', 'SGPA', 'CGPA', 'Result', 'Term Grade']])

    def _filter_students(self, *args):
        """Re-render student table based on search text and result filter."""
        df = self.df
        q = self.search_var.get().strip().lower()
        filt = self.result_filter.get()

        # Apply search filter
        if q:
            mask = (df['USN'].str.lower().str.contains(q, na=False) |
                    df['Name'].str.lower().str.contains(q, na=False) |
                    df['Serial'].str.contains(q, na=False))
            df = df[mask]

        # Apply result filter
        if filt != "All":
            df = df[df['Result'] == filt]

        self.student_count_label.configure(text=f"Showing {len(df)} students")
        for w in self.student_table_frame.winfo_children():
            w.destroy()
        self._render_table(self.student_table_frame, df[['Serial', 'USN', 'Name', 'SGPA', 'CGPA', 'Result', 'Term Grade']])

    # ════════════════ VIEW 3: SUBJECTS ════════════════
    def _render_subjects(self):
        """Course cards grid + subject-wise average GP chart."""
        if not self.data or not self.data['courses']:
            ctk.CTkLabel(self.content_frame, text="No course data found in the PDF.",
                         font=ctk.CTkFont(size=16), text_color=COLORS['text_dim']).pack(pady=50)
            return

        ctk.CTkLabel(self.content_frame, text="📚  Course Index",
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=COLORS['text']
                     ).pack(anchor="w", padx=20, pady=(15, 10))

        # Course cards in a 2-column grid
        grid = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        grid.pack(fill="x", padx=20, pady=10)
        for idx, course in enumerate(self.data['courses']):
            grid.grid_columnconfigure(idx % 2, weight=1)
            card = ctk.CTkFrame(grid, corner_radius=12, fg_color=COLORS['bg_card'])
            card.grid(row=idx // 2, column=idx % 2, padx=6, pady=6, sticky="nsew")
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=15, pady=12, fill="x")
            ctk.CTkLabel(inner, text=course['code'], font=ctk.CTkFont(size=14, weight="bold"),
                         text_color=COLORS['info']).pack(anchor="w")
            ctk.CTkLabel(inner, text=course['name'], font=ctk.CTkFont(size=12),
                         text_color=COLORS['text'], wraplength=350).pack(anchor="w", pady=(3, 0))

        # Subject-wise average GP chart
        gp_cols = [c for c in self.df.columns if c.endswith('_GP')]
        if not gp_cols:
            return

        ctk.CTkLabel(self.content_frame, text="📊  Subject-wise Analysis",
                     font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS['text']
                     ).pack(anchor="w", padx=20, pady=(20, 10))

        fig, ax = self._make_chart(self.content_frame, figsize=(10, max(4, len(gp_cols) * 0.6)))
        stats = {}
        for col in gp_cols:
            valid = self.df[col][self.df[col] > 0]
            if not valid.empty:
                stats[col.replace('_GP', '')] = valid.mean()

        if stats:
            codes, avg_gps = zip(*stats.items())
            colors = [COLORS['success'] if g >= 7 else COLORS['info'] if g >= 5
                      else COLORS['warning'] if g >= 3 else COLORS['danger'] for g in avg_gps]
            bars = ax.barh(list(codes), list(avg_gps), color=colors, height=0.6, edgecolor='#0d1117')
            ax.set_xlim(0, 10)
            ax.set_xlabel("Average Grade Point", color='white', fontsize=10)
            ax.set_title("Average GP per Subject", color='white', fontsize=13, pad=15, fontweight='bold')
            for bar, val in zip(bars, avg_gps):
                ax.text(bar.get_width() + 0.15, bar.get_y() + bar.get_height() / 2,
                        f'{val:.1f}', va='center', color='white', fontsize=10, fontweight='bold')
            fig.tight_layout()
        self._embed_chart(fig, self.content_frame).pack(fill="x", padx=26, pady=10)

    # ════════════════ VIEW 4: ANALYTICS ════════════════
    def _render_analytics(self):
        """CGPA histogram, SGPA vs CGPA scatter, stats summary, boxplot by grade."""
        df = self.df
        if df is None or df.empty:
            return

        ctk.CTkLabel(self.content_frame, text="📈  Advanced Analytics",
                     font=ctk.CTkFont(size=20, weight="bold"), text_color=COLORS['text']
                     ).pack(anchor="w", padx=20, pady=(15, 10))

        # Row: CGPA histogram + SGPA vs CGPA scatter
        row1 = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        row1.pack(fill="x", padx=20, pady=10)
        row1.grid_columnconfigure((0, 1), weight=1)

        # CGPA histogram
        fig1, ax1 = self._make_chart(row1)
        valid_cgpa = df['CGPA'][df['CGPA'] > 0]
        if not valid_cgpa.empty:
            ax1.hist(valid_cgpa, bins=np.arange(0, 10.5, 0.5), color=COLORS['purple'],
                     edgecolor='#0d1117', alpha=0.85, rwidth=0.9)
            ax1.axvline(valid_cgpa.mean(), color=COLORS['gold'], linestyle='--',
                        linewidth=2, label=f'Mean: {valid_cgpa.mean():.2f}')
            ax1.legend(fontsize=9)
        ax1.set_xlabel("CGPA", color='white', fontsize=10)
        ax1.set_ylabel("Students", color='white', fontsize=10)
        ax1.set_title("CGPA Distribution", color='white', fontsize=13, pad=15, fontweight='bold')
        self._embed_chart(fig1, row1).grid(row=0, column=0, padx=6, pady=5, sticky="nsew")

        # Scatter: SGPA vs CGPA (green=pass, red=fail)
        fig2, ax2 = self._make_chart(row1)
        valid = df[(df['SGPA'] > 0) & (df['CGPA'] > 0)]
        if not valid.empty:
            c = [COLORS['success'] if r == 'PASS' else COLORS['danger'] for r in valid['Result']]
            ax2.scatter(valid['SGPA'], valid['CGPA'], c=c, alpha=0.7, s=50, edgecolors='white', linewidth=0.5)
            ax2.plot([0, 10], [0, 10], '--', color=COLORS['text_dim'], alpha=0.4)  # Diagonal reference
        ax2.set_xlabel("SGPA", color='white', fontsize=10)
        ax2.set_ylabel("CGPA", color='white', fontsize=10)
        ax2.set_title("SGPA vs CGPA", color='white', fontsize=13, pad=15, fontweight='bold')
        ax2.set_xlim(0, 10)
        ax2.set_ylim(0, 10)
        self._embed_chart(fig2, row1).grid(row=0, column=1, padx=6, pady=5, sticky="nsew")

        # ── Statistical summary grid ──
        stats_frame = ctk.CTkFrame(self.content_frame, corner_radius=12, fg_color=COLORS['bg_card'])
        stats_frame.pack(fill="x", padx=26, pady=10)
        ctk.CTkLabel(stats_frame, text="📋  Statistical Summary",
                     font=ctk.CTkFont(size=15, weight="bold"), text_color=COLORS['text']
                     ).pack(anchor="w", padx=15, pady=(12, 8))

        sgrid = ctk.CTkFrame(stats_frame, fg_color="transparent")
        sgrid.pack(fill="x", padx=15, pady=(0, 15))
        sgrid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        valid_sgpa = df['SGPA'][df['SGPA'] > 0]
        # Helper to format stats safely
        def fmt(series, func):
            return f"{func(series):.2f}" if not series.empty else "N/A"

        for i, (label, value) in enumerate([
            ("SGPA Range", f"{fmt(valid_sgpa, min)} – {fmt(valid_sgpa, max)}"),
            ("CGPA Range", f"{fmt(valid_cgpa, min)} – {fmt(valid_cgpa, max)}"),
            ("Median SGPA", fmt(valid_sgpa, lambda s: s.median())),
            ("Median CGPA", fmt(valid_cgpa, lambda s: s.median())),
            ("Std Dev SGPA", fmt(valid_sgpa, lambda s: s.std())),
            ("Std Dev CGPA", fmt(valid_cgpa, lambda s: s.std())),
            ("Highest SGPA", fmt(valid_sgpa, max)),
            ("Lowest SGPA", fmt(valid_sgpa, min)),
        ]):
            cell = ctk.CTkFrame(sgrid, fg_color=COLORS['accent_1'], corner_radius=8)
            cell.grid(row=i // 4, column=i % 4, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11),
                         text_color=COLORS['text_dim']).pack(pady=(8, 2))
            ctk.CTkLabel(cell, text=value, font=ctk.CTkFont(size=16, weight="bold"),
                         text_color=COLORS['text']).pack(pady=(0, 8))

        # ── Boxplot: SGPA grouped by Term Grade ──
        fig3, ax3 = self._make_chart(self.content_frame, figsize=(10, 4))
        grade_groups = df[df['SGPA'] > 0].groupby('Term Grade')['SGPA']
        data_list, labels = [], []
        for name, group in grade_groups:
            if len(group) >= 1 and name:
                data_list.append(group.values)
                labels.append(name)
        if data_list:
            ax3.boxplot(data_list, tick_labels=labels, patch_artist=True,
                        boxprops=dict(facecolor=COLORS['info'], alpha=0.7),
                        medianprops=dict(color=COLORS['gold'], linewidth=2),
                        whiskerprops=dict(color='white'), capprops=dict(color='white'),
                        flierprops=dict(markerfacecolor=COLORS['accent_2'], marker='o'))
        ax3.set_title("SGPA Distribution by Term Grade", color='white', fontsize=13, pad=15, fontweight='bold')
        ax3.set_ylabel("SGPA", color='white', fontsize=10)
        ax3.tick_params(axis='x', rotation=15, labelsize=9)
        fig3.tight_layout()
        self._embed_chart(fig3, self.content_frame).pack(fill="x", padx=26, pady=10)

    # ════════════════ TABLE RENDERER ════════════════
    def _render_table(self, parent, df, highlight_top=False):
        """Render a DataFrame as a styled table with colored Result column."""
        if df.empty:
            ctk.CTkLabel(parent, text="No data to display.",
                         text_color=COLORS['text_dim']).pack(pady=20)
            return

        table = ctk.CTkFrame(parent, fg_color="transparent")
        table.pack(fill="x", padx=10, pady=(0, 10))
        cols = list(df.columns)
        for j in range(len(cols)):
            table.grid_columnconfigure(j, weight=1)

        # Header row
        for j, col in enumerate(cols):
            ctk.CTkLabel(table, text=col, font=ctk.CTkFont(size=11, weight="bold"),
                         text_color=COLORS['text'], fg_color=COLORS['accent_1'],
                         corner_radius=4 if j in (0, len(cols) - 1) else 0,
                         padx=8, pady=6).grid(row=0, column=j, sticky="nsew", padx=0, pady=(0, 1))

        # Data rows (alternating background colors)
        for i, (_, row) in enumerate(df.iterrows()):
            bg = '#1c2333' if i % 2 == 0 else '#151d2b'
            for j, col in enumerate(cols):
                val = row[col]
                # Color-code the Result column
                tc = COLORS['text']
                if col == 'Result':
                    tc = COLORS['success'] if val == 'PASS' else COLORS['danger'] if val == 'FAIL' else tc
                if highlight_top and i == 0 and col in ('Name', 'SGPA'):
                    tc = COLORS['gold']  # Gold highlight for #1 student

                ctk.CTkLabel(table, text=str(val) if pd.notna(val) else "",
                             font=ctk.CTkFont(size=11), text_color=tc,
                             fg_color=bg, padx=8, pady=5).grid(row=i + 1, column=j, sticky="nsew", padx=0, pady=0)

    # ════════════════ EXPORT TO EXCEL ════════════════
    def export_excel(self):
        """Save all parsed data to a multi-sheet Excel file."""
        if self.df is None or self.df.empty:
            messagebox.showinfo("No Data", "Upload a PDF first before exporting.")
            return

        filepath = filedialog.asksaveasfilename(
            title="Save Excel File", defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")],
            initialfile="result_analysis.xlsx"
        )
        if not filepath:
            return

        try:
            export_pretty_excel(filepath, self.data, self.df)
            messagebox.showinfo("Export Successful", f"Professional Excel report exported to:\n{filepath}")
        except PermissionError:
            messagebox.showerror(
                "File in Use",
                f"Cannot save the file because it is currently open in Microsoft Excel or another program:\n\n{filepath}\n\nPlease close the file in Excel and try exporting again."
            )
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export Excel report:\n{str(e)}")

    # ════════════════ CLEAR DATA ════════════════
    def clear_data(self):
        """Reset the app back to the welcome screen."""
        # Close all charts and clear content
        for fig in self.active_figs:
            plt.close(fig)
        self.active_figs.clear()
        for w in self.content_frame.winfo_children():
            w.destroy()

        # Reset state
        self.data = None
        self.df = None
        self.parser = TabulationParser()
        self.file_label.configure(text="")

        # Hide nav buttons, show welcome screen
        for btn in self.nav_buttons.values():
            btn.grid_remove()
        self.export_btn.grid_remove()
        self.content_frame.grid_forget()
        self.welcome_frame.grid(row=0, column=0, sticky="nsew")
