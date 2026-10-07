"""Main application window: launch screen <-> main shell (sidebar, top bar, panes, status bar)."""
from __future__ import annotations

import os
import queue
import subprocess
import sys
import threading
import traceback
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))
import core
from . import theme as T
from .components import Line, AppButton, Pane, rich
from .theme import F

try:                                    # optional: drag & drop of PDFs onto the launch screen
    from tkinterdnd2 import TkinterDnD
    _DnDBase = TkinterDnD.DnDWrapper
except Exception:                       # pragma: no cover
    TkinterDnD = None

    class _DnDBase:                     # type: ignore
        pass

TABS = [  # key, icon kind, icon, label
    ("dashboard", "glyph", "⊞", "Overview"),
    ("students", "emoji", "users", "Student Register"),
    ("subjects", "emoji", "chart_up", "Subject Analysis"),
    ("failures", "emoji", "warning", "Failed Students"),
    ("toppers", "emoji", "trophy", "Toppers & Merit"),
    ("export", "emoji", "inbox", "Export & Reports"),
]
TITLES = {
    "dashboard": "Overview & Dashboard", "students": "Student Register & Mark Cards",
    "subjects": "Subject Performance Analytics", "failures": "Remedial Register & Backlogs",
    "toppers": "Toppers & Merit Rankings", "cohort": "Year-Type Analysis", "export": "Reports & Export Workspace",
}


def _builder(key):
    from . import (backlog_view, dashboard_view, export_view, failures_view, students_view, subjects_view,
                   toppers_view)
    return {"dashboard": dashboard_view.build, "students": students_view.build, "subjects": subjects_view.build,
            "failures": failures_view.build, "toppers": toppers_view.build, "cohort": backlog_view.build,
            "export": export_view.build}[key]


# ==========================================================================================
class NavTab(ctk.CTkFrame):
    """.nav-tab : icon + label (+ count pill). Active = dark fill with a red left edge."""

    HOVER = T.blend("#ffffff", .06, T.SIDEBAR_BG)

    def __init__(self, master, icon_kind, icon, text, count, warn, command):
        super().__init__(master, fg_color="transparent", corner_radius=T.R_MD, height=40)
        self.pack_propagate(False)
        self.command, self.active, self.warn = command, False, warn
        self.stripe = ctk.CTkFrame(self, fg_color=T.RED, corner_radius=T.R_MD, width=16, bg_color=T.SIDEBAR_BG)
        self.inner = ctk.CTkFrame(self, fg_color="transparent", corner_radius=T.R_MD, bg_color=T.SIDEBAR_BG)
        self.inner.place(x=0, y=0, relwidth=1, relheight=1)
        if icon_kind == "emoji":
            self.icon = ctk.CTkLabel(self.inner, text="", image=T.emoji(icon, 16), width=20)
        else:
            self.icon = ctk.CTkLabel(self.inner, text=icon, font=F("ui", 16), text_color=T.SIDEBAR_TEXT, width=20)
        self.icon.pack(side="left", padx=(14, 12))
        self.label = ctk.CTkLabel(self.inner, text=text, font=F("ui5", 13), text_color=T.SIDEBAR_TEXT, anchor="w")
        self.label.pack(side="left")
        self.pill = None
        if count is not None:
            txt = str(count)
            self.pill = ctk.CTkLabel(self.inner, text=txt, font=F("mono", 11), height=20,
                                     width=max(26, 8 * len(txt) + 16), corner_radius=10)
            self.pill.pack(side="right", padx=(0, 14))
        self._paint()
        for w in (self, self.inner, self.icon, self.label, *([self.pill] if self.pill else [])):
            w.bind("<Button-1>", lambda e: self.command(), add="+")
            w.bind("<Enter>", lambda e: self._hover(True), add="+")
            w.bind("<Leave>", lambda e: self._leave(e), add="+")
            w.configure(cursor="hand2")

    def _paint(self, hover=False):
        if self.active:
            self.stripe.place(x=0, y=0, relheight=1)
            self.inner.place_configure(x=3, relwidth=1, width=-3)
            self.inner.lift()
            self.inner.configure(fg_color=T.SIDEBAR_ACTIVE_BG)
            self.label.configure(text_color="#ffffff", font=F("ui6", 13))
            base = T.SIDEBAR_ACTIVE_BG
        else:
            self.stripe.place_forget()
            self.inner.place_configure(x=0, relwidth=1, width=0)
            base = self.HOVER if hover else T.SIDEBAR_BG
            self.inner.configure(fg_color=self.HOVER if hover else "transparent")
            self.label.configure(text_color=T.SIDEBAR_TEXT_HOVER if hover else T.SIDEBAR_TEXT, font=F("ui5", 13))
            if isinstance(self.icon.cget("text"), str) and self.icon.cget("text"):
                self.icon.configure(text_color=T.SIDEBAR_TEXT_HOVER if hover else T.SIDEBAR_TEXT)
        if self.active and self.icon.cget("text"):
            self.icon.configure(text_color="#ffffff")
        if self.pill:
            if self.warn:
                self.pill.configure(fg_color=T.blend("#ef4444", .20, base), text_color="#fca5a5")
            else:
                self.pill.configure(fg_color=T.blend("#ffffff", .10, base), text_color="#cbd5e1")

    def _hover(self, on):
        if not self.active:
            self._paint(on)

    def _leave(self, e):
        w = self.winfo_containing(e.x_root, e.y_root)
        while w is not None and w is not self:
            w = getattr(w, "master", None)
        if w is not self and not self.active:
            self._paint(False)

    def set_active(self, on: bool):
        self.active = on
        self._paint()


# ==========================================================================================
class AppShell(ctk.CTkFrame):
    def __init__(self, master, data: dict, app: "MainWindow"):
        super().__init__(master, fg_color=T.CANVAS_BG, corner_radius=0)
        self.data, self.app = data, app
        self._panes: dict[str, Pane] = {}
        self._tabs: dict[str, NavTab] = {}
        self.current = None
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_workspace()
        self.show("dashboard")

    # ---- sidebar -------------------------------------------------------------------------
    def _build_sidebar(self):
        s = self.data["summary"]
        sb = ctk.CTkFrame(self, width=260, fg_color=T.SIDEBAR_BG, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.pack_propagate(False)
        ctk.CTkFrame(sb, width=1, fg_color=T.SIDEBAR_BORDER, corner_radius=0).place(relx=1, x=-1, y=0, relheight=1)

        brand = ctk.CTkFrame(sb, fg_color="transparent")
        brand.pack(fill="x", padx=16, pady=16)
        ctk.CTkLabel(brand, text="Result Analyzer", font=F("brand", 17), text_color="#ffffff"
                     ).pack(side="left")
        Line(sb, T.blend("#ffffff", .06, T.SIDEBAR_BG)).pack(fill="x")

        chip = ctk.CTkFrame(sb, fg_color=T.blend("#ffffff", .04, T.SIDEBAR_BG), border_width=1,
                            border_color=T.blend("#ffffff", .08, T.SIDEBAR_BG), corner_radius=T.R_MD)
        chip.pack(fill="x", padx=14, pady=12)
        ctk.CTkLabel(chip, text="ACTIVE LEDGER", font=F("ui7", 9), text_color="#64748b", anchor="w"
                     ).pack(fill="x", padx=12, pady=(10, 3))
        name_font = T.TkF("ui6", 12, T.scale_of(chip))
        name = T.ellipsize(self.data["filename"] or "-", name_font, 196 * T.scale_of(chip))
        ctk.CTkLabel(chip, text=name, font=F("ui6", 12), text_color="#e2e8f0", anchor="w").pack(fill="x", padx=12)
        ctk.CTkLabel(chip, text=f"●  {s['total']} records loaded", font=F("ui", 11), text_color=T.GREEN, anchor="w"
                     ).pack(fill="x", padx=12, pady=(2, 10))

        nav = ctk.CTkFrame(sb, fg_color="transparent")
        nav.pack(fill="x", padx=10, pady=8)
        counts = {"students": (s["total"], False), "subjects": (len(self.data["subjects"]), False),
                  "failures": (s["failed"], True)}
        for key, kind, icon, label in TABS:
            cnt, warn = counts.get(key, (None, False))
            tab = NavTab(nav, kind, icon, label, cnt, warn, lambda k=key: self.show(k))
            tab.pack(fill="x", pady=(0, 4))
            self._tabs[key] = tab

        foot = ctk.CTkFrame(sb, fg_color="transparent")
        foot.pack(side="bottom", fill="x")
        Line(foot, T.blend("#ffffff", .06, T.SIDEBAR_BG)).pack(fill="x")
        AppButton(foot, "Open Another PDF", "sb_outline", self.app.open_another, image=T.icon("upload_light", 15),
                  height=36).pack(fill="x", padx=14, pady=(14, 8))
        AppButton(foot, "Export Excel", "sb_primary", self.app.export_excel, image=T.icon("download_white", 15),
                  height=36).pack(fill="x", padx=14, pady=(0, 14))

    # ---- workspace (top bar, notice, viewport, status bar) ---------------------------------
    def _build_workspace(self):
        s, warnings = self.data["summary"], self.data.get("warnings") or []
        ws = ctk.CTkFrame(self, fg_color=T.CANVAS_BG, corner_radius=0)
        ws.grid(row=0, column=1, sticky="nsew")
        ws.grid_columnconfigure(0, weight=1)
        ws.grid_rowconfigure(2, weight=1)

        top = ctk.CTkFrame(ws, height=56, fg_color=T.PANEL, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew")
        top.pack_propagate(False)
        Line(top, T.BORDER).pack(side="bottom", fill="x")
        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", padx=(24, 0), fill="y")
        self.title_lbl = ctk.CTkLabel(left, text=TITLES["dashboard"], font=F("ui7", 17), text_color=T.TEXT, anchor="w")
        self.title_lbl.pack(anchor="w", pady=(7, 0))
        meta = self.data.get("metadata", {})
        fmt = self.data.get("format_type", "Official Analysis")
        prog_sem = f"{meta.get('program', 'Degree')} {('Semester ' + meta.get('semester')) if meta.get('semester') else ''}".strip()
        sub_title = f"{prog_sem} · {fmt}" if prog_sem else fmt
        ctk.CTkLabel(left, text=sub_title, font=F("ui", 11), text_color=T.MUTED,
                     anchor="w").pack(anchor="w")
        acts = ctk.CTkFrame(top, fg_color="transparent")
        acts.pack(side="right", padx=(0, 24), fill="y")
        AppButton(acts, "Excel Report", "accent", self.app.export_excel, image=T.icon("download_white", 16),
                  height=34).pack(side="right", pady=11)
        for label, num, pct, color in (("Failed: ", s["failed"], s["fail_percentage"], T.RED),
                                       ("Passed: ", s["passed"], s["pass_percentage"], T.GREEN)):
            pill = ctk.CTkFrame(acts, fg_color="#f1f5f9", corner_radius=20)
            pill.pack(side="right", padx=(0, 10), pady=11)
            ctk.CTkFrame(pill, width=8, height=8, fg_color=color, corner_radius=4).pack(side="left", padx=(10, 6), pady=11)
            rich(pill, [(label, "ui", 12, T.TEXT2), (str(num), "ui7", 12, T.TEXT2), (f" ({pct}%)", "ui", 12, T.TEXT2)]
                 ).pack(side="left", padx=(0, 10))

        left = ctk.CTkFrame(top, fg_color="transparent")
        left.pack(side="left", padx=(24, 8), fill="both", expand=True)
        self.title_lbl = ctk.CTkLabel(left, text=TITLES["dashboard"], font=F("ui7", 17), text_color=T.TEXT, anchor="w")
        self.title_lbl.pack(anchor="w", pady=(7, 0))
        meta = self.data.get("metadata", {})
        fmt = self.data.get("format_type", "Official Analysis")
        prog_sem = f"{meta.get('program', 'Degree')} {('Semester ' + meta.get('semester')) if meta.get('semester') else ''}".strip()
        sub_title = f"{prog_sem} · {fmt}" if prog_sem else fmt
        ctk.CTkLabel(left, text=sub_title, font=F("ui", 11), text_color=T.MUTED,
                     anchor="w").pack(anchor="w")

        if warnings:
            nb = ctk.CTkFrame(ws, fg_color="#fffbeb", corner_radius=0, height=36)
            nb.grid(row=1, column=0, sticky="ew")
            nb.pack_propagate(False)
            Line(nb, "#fef3c7").pack(side="bottom", fill="x")
            ctk.CTkLabel(nb, text="⚠", font=F("ui", 13), text_color="#92400e").pack(side="left", padx=(24, 8))
            n = len(warnings)
            rich(nb, [(str(n), "ui7", 12, "#92400e"),
                      (f" source validation warning{'' if n == 1 else 's'} retained from the original PDF records.",
                       "ui", 12, "#92400e")]).pack(side="left")
            link_font = ctk.CTkFont(family=T._resolve("ui7")[0], size=12, weight="bold", underline=True)
            ctk.CTkButton(nb, text="View in Reports", font=link_font, fg_color="transparent", hover=False,
                          text_color="#b45309", width=10, height=24, cursor="hand2",
                          command=lambda: self.show("export")).pack(side="right", padx=24)

        self.viewport = ctk.CTkFrame(ws, fg_color=T.CANVAS_BG, corner_radius=0)
        self.viewport.grid(row=2, column=0, sticky="nsew")
        self.viewport.grid_rowconfigure(0, weight=1)
        self.viewport.grid_columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(ws, height=28, fg_color=T.WIN_BG, corner_radius=0)
        bar.grid(row=3, column=0, sticky="ew")
        bar.pack_propagate(False)
        Line(bar, T.blend("#ffffff", .08, T.WIN_BG)).pack(side="top", fill="x")
        div, grey, white = T.blend("#ffffff", .15, T.WIN_BG), T.LIGHT, "#cbd5e1"
        L = ctk.CTkFrame(bar, fg_color="transparent")
        L.pack(side="left", padx=(16, 0))
        ctk.CTkFrame(L, width=7, height=7, fg_color=T.GREEN, corner_radius=4).pack(side="left", padx=(0, 8))
        self.status_text = ctk.CTkLabel(L, text="Ready", font=F("ui", 11), text_color=grey)
        self.status_text.pack(side="left")
        ctk.CTkLabel(L, text="  |  ", font=F("ui", 11), text_color=div).pack(side="left")
        raw_fname = str(self.data.get("filename") or "-")
        disp_fname = raw_fname if len(raw_fname) <= 20 else raw_fname[:17] + "..."
        rich(L, [("Ledger: ", "ui", 11, grey), (disp_fname, "ui7", 11, grey)]).pack(side="left")
        ctk.CTkLabel(L, text="  |  ", font=F("ui", 11), text_color=div).pack(side="left")
        rich(L, [("Records: ", "ui", 11, grey), (str(s["total"]), "ui7", 11, grey)]).pack(side="left")
        R = ctk.CTkFrame(bar, fg_color="transparent")
        R.pack(side="right", padx=(0, 16))
        ctk.CTkLabel(R, text="UTF-8", font=F("ui", 11), text_color=grey).pack(side="left")
        ctk.CTkLabel(R, text="  |  ", font=F("ui", 11), text_color=div).pack(side="left")
        ctk.CTkLabel(R, text="Result Analyzer", font=F("brand", 11), text_color=white).pack(side="left")
        C = rich(bar, [("Pass Rate: ", "ui", 11, grey), (f"{s['pass_percentage']}%", "ui7", 11, grey),
                       ("  ·  ", "ui", 11, div), ("Absent: ", "ui", 11, grey), (str(s["absent"]), "ui7", 11, grey)])
        C.place(relx=.5, rely=.5, anchor="center")

    # ---- navigation ---------------------------------------------------------------------------
    def show(self, key: str):
        if key not in self._panes:
            self.configure(cursor="watch")
            self.update_idletasks()
            pane = Pane(self.viewport)
            _builder(key)(pane.body, self.data, self)
            pane.grid(row=0, column=0, sticky="nsew")
            self._panes[key] = pane
            self.configure(cursor="")
        for k, p in self._panes.items():
            if k == key:
                p.grid()
            else:
                p.grid_remove()
        for k, tab in self._tabs.items():
            tab.set_active(k == key)
        self.title_lbl.configure(text=TITLES[key])
        self.current = key

    def export_excel(self):
        self.app.export_excel()


# ==========================================================================================
class MainWindow(ctk.CTk, _DnDBase):
    def __init__(self):
        T.register_fonts()
        ctk.set_appearance_mode("light")
        super().__init__(fg_color=T.WIN_BG)
        self.dnd_ok = False
        if TkinterDnD is not None:
            try:
                self.TkdndVersion = TkinterDnD._require(self)
                self.dnd_ok = True
            except Exception:
                self.dnd_ok = False

        self.title("Result Analyzer")
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        s = T.scale_of(self)
        w, h = int(min(1366, sw / s - 60)), int(min(840, sh / s - 90))
        self.geometry(f"{w}x{h}+{max(0, int((sw / s - w) / 2))}+{max(0, int((sh / s - h) / 3))}")
        self.minsize(1100, 700)
        T.set_window_icon(self)
        T.style_titlebar(self)

        self.data: dict | None = None
        self.shell: AppShell | None = None
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        from .upload_view import UploadView
        self.upload = UploadView(self, self.start_analysis, dnd=self.dnd_ok)
        self.upload.grid(row=0, column=0, sticky="nsew")
        self.bind_all("<Control-w>", lambda e: self.close_ledger())
        self.bind_all("<Control-o>", lambda e: self.open_another(confirm=False))
        self.bind_all("<F11>", self.toggle_fullscreen)
        self.bind_all("<Escape>", self.exit_fullscreen)
        self.bind_all("<MouseWheel>", self._on_global_mousewheel, add="+")
        self.bind_all("<Button-4>", lambda e: self._on_global_mousewheel(e, direction=1), add="+")
        self.bind_all("<Button-5>", lambda e: self._on_global_mousewheel(e, direction=-1), add="+")
        self.bind_all("<Key>", self._on_global_key, add="+")
        self.report_callback_exception = self._on_error

    def toggle_fullscreen(self, event=None):
        is_fs = bool(self.attributes("-fullscreen"))
        self.attributes("-fullscreen", not is_fs)

    def exit_fullscreen(self, event=None):
        if self.attributes("-fullscreen"):
            self.attributes("-fullscreen", False)

    # ---- scrolling & keyboard navigation ------------------------------------------------------
    def _on_global_mousewheel(self, event, direction=None):
        if not self.shell or not self.shell.current or self.shell.current not in self.shell._panes:
            return
        active_pane = self.shell._panes[self.shell.current]

        # Determine widget directly under the pointer
        widget = event.widget
        if hasattr(event, "x_root") and hasattr(event, "y_root"):
            try:
                containing = self.winfo_containing(event.x_root, event.y_root)
                if containing is not None:
                    widget = containing
            except Exception:
                pass

        # Check if the widget is within this application window
        w = widget
        is_ours = False
        while w is not None:
            if w is self:
                is_ours = True
                break
            w = getattr(w, "master", None)
        if not is_ours:
            return

        # Check if the cursor is hovering over an inner DataTable that has vertical scroll room
        from .components import DataTable
        w = widget
        dt_instance = None
        while w is not None:
            if isinstance(w, DataTable):
                dt_instance = w
                break
            w = getattr(w, "master", None)

        if dt_instance is not None and dt_instance._max_scroll() > 0:
            res = dt_instance._on_wheel(event, direction=direction)
            if res == "break":
                return "break"

        # Otherwise scroll the active pane if the pointer is within the viewport or workspace
        w = widget
        in_viewport = False
        while w is not None:
            if w is self.shell.viewport or w is active_pane or w is active_pane._parent_canvas or w is active_pane.body:
                in_viewport = True
                break
            w = getattr(w, "master", None)

        if in_viewport:
            if direction is not None:
                units = -direction * 3
            elif sys.platform.startswith("win"):
                units = -int(event.delta / 120) * 3
                if units == 0 and event.delta != 0:
                    units = -1 if event.delta > 0 else 1
            elif sys.platform == "darwin":
                units = -int(event.delta)
            else:
                units = 3

            try:
                active_pane._parent_canvas.yview("scroll", units, "units")
            except Exception:
                pass
            return "break"

    def _on_global_key(self, event):
        if not self.shell or not self.shell.current or self.shell.current not in self.shell._panes:
            return
        active_pane = self.shell._panes[self.shell.current]

        try:
            focus = self.focus_get()
            import tkinter as _tk
            if isinstance(focus, (ctk.CTkEntry, _tk.Entry, ctk.CTkTextbox, _tk.Text)):
                return
        except Exception:
            pass

        if event.keysym == "Up":
            active_pane._parent_canvas.yview("scroll", -2, "units")
            return "break"
        elif event.keysym == "Down":
            active_pane._parent_canvas.yview("scroll", 2, "units")
            return "break"
        elif event.keysym in ("Prior", "Page_Up"):
            active_pane._parent_canvas.yview("scroll", -1, "pages")
            return "break"
        elif event.keysym in ("Next", "Page_Down"):
            active_pane._parent_canvas.yview("scroll", 1, "pages")
            return "break"
        elif event.keysym == "Home":
            active_pane._parent_canvas.yview("moveto", 0.0)
            return "break"
        elif event.keysym == "End":
            active_pane._parent_canvas.yview("moveto", 1.0)
            return "break"

    # ---- analysis ---------------------------------------------------------------------------
    def start_analysis(self, path: str):
        self.upload.set_busy(True)
        q: queue.Queue = queue.Queue()

        def work():
            try:
                q.put(("ok", core.analyze_pdf_file(path)))
            except core.AnalysisError as err:
                q.put(("err", str(err)))
            except Exception:
                traceback.print_exc()
                q.put(("err", "Unable to analyze this PDF. The file may not contain a supported result format."))

        threading.Thread(target=work, daemon=True).start()
        self.after(60, self._poll, q)

    def _poll(self, q: queue.Queue):
        try:
            kind, payload = q.get_nowait()
        except queue.Empty:
            self.after(60, self._poll, q)
            return
        if kind == "err":
            self.upload.set_busy(False)
            self.upload.show_error(payload)
            return
        try:
            self.show_analysis(payload)
        except Exception as err:        # building the dashboard failed - never leave the user on a frozen screen
            self._on_error(type(err), err, err.__traceback__)
            self.upload.set_busy(False)
            self.upload.show_error("The result was analysed but the dashboard could not be displayed.")

    def show_analysis(self, data: dict):
        self.data = data
        if self.shell is not None:
            self.shell.destroy()
        self.upload.grid_remove()
        self.shell = AppShell(self, data, self)
        self.shell.grid(row=0, column=0, sticky="nsew")
        self.shell.tkraise()
        self.upload.set_busy(False)

    # ---- reset / open another -----------------------------------------------------------------
    def close_ledger(self):
        if self.shell is None:
            return
        self.shell.destroy()
        self.shell = None
        self.data = None
        self.upload.reset()
        self.upload.grid(row=0, column=0, sticky="nsew")
        import tkinter as _tk
        _tk.Misc.tkraise(self.upload)

    def open_another(self, confirm: bool = True):
        if self.shell is None:
            self.upload.browse()
            return
        if confirm and not messagebox.askyesno("Result Analyzer", "Switch to another PDF? The current ledger will be reset.",
                                              parent=self):
            return
        self.close_ledger()

    # ---- Excel export -------------------------------------------------------------------------
    def export_excel(self):
        if not self.data:
            messagebox.showinfo("Result Analyzer", "Please upload a result PDF first.", parent=self)
            return

        # Determine intuitive initial directory:
        # 1. Directory last chosen by user during this session
        # 2. Directory of the currently loaded PDF ledger
        # 3. User's Desktop
        # 4. User's Downloads folder
        init_dir = getattr(self, "_last_export_dir", None)
        if not init_dir or not Path(init_dir).exists():
            pdf_path = getattr(self.upload, "path", None)
            if pdf_path and Path(pdf_path).parent.exists():
                init_dir = str(Path(pdf_path).parent)
            else:
                desktop = Path.home() / "Desktop"
                downloads = Path.home() / "Downloads"
                init_dir = str(desktop if desktop.exists() else (downloads if downloads.exists() else Path.home()))

        default_name = core.default_export_name(self.data.get("metadata") if self.data else None)

        path = filedialog.asksaveasfilename(
            parent=self,
            title="Save Excel Report - Select Location",
            defaultextension=".xlsx",
            initialdir=init_dir,
            initialfile=default_name,
            filetypes=[("Excel Workbook (*.xlsx)", "*.xlsx"), ("All Files (*.*)", "*.*")],
        )
        if not path:
            return

        self._last_export_dir = str(Path(path).parent)
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            saved = core.export_excel_file(self.data, path)
        except PermissionError:
            messagebox.showerror("Export failed", "Permission denied. The file may be open in Excel or the folder is "
                                 "read-only.\n\nClose the file or choose another location and try again.", parent=self)
            return
        except Exception as err:
            traceback.print_exc()
            messagebox.showerror("Export failed", f"The Excel report could not be created.\n\n{err}", parent=self)
            return
        finally:
            self.configure(cursor="")
        if messagebox.askyesno("Excel Report Saved", f"Report saved successfully to:\n\n{saved}\n\nOpen it now?", parent=self):
            self._open_file(saved)

    @staticmethod
    def _open_file(path: Path):
        try:
            if sys.platform.startswith("win"):
                os.startfile(str(path))            # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception:
            pass

    # ---- unhandled errors ---------------------------------------------------------------------
    def _on_error(self, exc, val, tb):
        text = "".join(traceback.format_exception(exc, val, tb))
        try:
            with open(core.BASE_DIR / "error.log", "a", encoding="utf-8") as fh:
                fh.write(f"\n[{datetime.now():%Y-%m-%d %H:%M:%S}]\n{text}")
        except Exception:
            pass
        print(text, file=sys.stderr)
        try:
            messagebox.showerror("Result Analyzer", f"Something went wrong:\n\n{val}\n\n(Details saved to error.log)", parent=self)
        except Exception:
            pass
