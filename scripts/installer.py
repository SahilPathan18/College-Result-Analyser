"""
Standalone Self-Extracting Installer for Result Analyzer.
Installs the complete application to %LOCALAPPDATA%\\ResultAnalyzer,
creates Desktop and Start Menu shortcuts with icons, and allows instant launch.
"""
from __future__ import annotations

import os
import sys
import shutil
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path


def get_special_folder(name: str) -> Path:
    """Get real path for Desktop or Programs, resolving OneDrive redirection."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        )
        val, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return Path(os.path.expandvars(val))
    except Exception:
        if name == "Desktop":
            return Path(os.environ.get("USERPROFILE", "")) / "Desktop"
        elif name == "Programs":
            return Path(os.environ.get("APPDATA", "")) / r"Microsoft\Windows\Start Menu\Programs"
        return Path.home()


def create_windows_shortcut(target_exe: str, shortcut_path: str, icon_path: str | None = None, desc: str = "Result Analyzer"):
    target_exe = str(target_exe).replace("'", "''")
    shortcut_path = str(shortcut_path).replace("'", "''")
    working_dir = os.path.dirname(target_exe).replace("'", "''")
    icon_loc = (icon_path or target_exe).replace("'", "''")

    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target_exe}'
    $Shortcut.WorkingDirectory = '{working_dir}'
    $Shortcut.IconLocation = '{icon_loc},0'
    $Shortcut.Description = '{desc}'
    $Shortcut.Save()
    """
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            capture_output=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
        )
    except Exception as e:
        print(f"Error creating shortcut {shortcut_path}: {e}")


class InstallerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Result Analyzer Setup")
        self.root.geometry("540x350")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b101d")

        # Center on screen
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"540x350+{(sw - 540) // 2}+{(sh - 350) // 2}")

        self.app_dir = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "ResultAnalyzer"
        self.app_exe = self.app_dir / "ResultAnalyzer.exe"

        # Apply icon if available
        self._set_icon()

        self._build_ui()
        self.root.after(400, self._start_install_thread)

    def _set_icon(self):
        meipass = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        for ico in (meipass / "assets" / "logo.ico", meipass / "ResultAnalyzer" / "assets" / "logo.ico"):
            if ico.exists():
                try:
                    self.root.iconbitmap(str(ico))
                    break
                except Exception:
                    pass

    def _build_ui(self):
        # Header banner
        header = tk.Frame(self.root, bg="#0f172a", height=85)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)

        title_lbl = tk.Label(header, text="Result Analyzer Setup", font=("Segoe UI", 16, "bold"),
                             fg="#ffffff", bg="#0f172a", anchor="w")
        title_lbl.pack(fill="x", padx=24, pady=(16, 2))

        sub_lbl = tk.Label(header, text="Bangalore University Result Analysis Desktop Application",
                           font=("Segoe UI", 9), fg="#94a3b8", bg="#0f172a", anchor="w")
        sub_lbl.pack(fill="x", padx=24)

        # Body container
        body = tk.Frame(self.root, bg="#0b101d")
        body.pack(fill="both", expand=True, padx=24, pady=16)

        self.status_lbl = tk.Label(body, text="Preparing installation...", font=("Segoe UI", 10),
                                   fg="#e2e8f0", bg="#0b101d", anchor="w")
        self.status_lbl.pack(fill="x", pady=(10, 8))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Horizontal.TProgressbar",
                        troughcolor="#1e293b",
                        background="#ea2839",
                        thickness=14,
                        borderwidth=0)

        self.progress = ttk.Progressbar(body, style="Custom.Horizontal.TProgressbar",
                                        orient="horizontal", mode="determinate", length=490)
        self.progress.pack(fill="x", pady=(0, 12))

        self.detail_lbl = tk.Label(body, text=f"Install location: {self.app_dir}",
                                   font=("Segoe UI", 8), fg="#64748b", bg="#0b101d", anchor="w")
        self.detail_lbl.pack(fill="x")

        # Bottom buttons container
        self.btn_frame = tk.Frame(self.root, bg="#0b101d")
        self.btn_frame.pack(fill="x", side="bottom", padx=24, pady=(0, 20))

        self.cancel_btn = tk.Button(self.btn_frame, text="Cancel", font=("Segoe UI", 9),
                                    bg="#1e293b", fg="#cbd5e1", activebackground="#334155",
                                    activeforeground="#ffffff", relief="flat", width=12,
                                    command=self.root.destroy)
        self.cancel_btn.pack(side="right")

    def _start_install_thread(self):
        t = threading.Thread(target=self._run_install, daemon=True)
        t.start()

    def _set_status(self, text: str, pct: float, detail: str = ""):
        def update():
            self.status_lbl.config(text=text)
            self.progress["value"] = pct
            if detail:
                self.detail_lbl.config(text=detail)
        self.root.after(0, update)

    def _run_install(self):
        try:
            self._set_status("Closing running application instances...", 5)
            # Terminate any running instances so files can be replaced cleanly
            try:
                subprocess.run(["taskkill", "/F", "/IM", "ResultAnalyzer.exe"],
                               capture_output=True,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                time.sleep(0.5)
            except Exception:
                pass

            meipass = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
            bundled_app_dir = Path(meipass) / "ResultAnalyzer"

            if not bundled_app_dir.exists():
                raise FileNotFoundError(f"Application package bundle not found in installer ({bundled_app_dir}).")

            self._set_status("Creating application directory...", 15)
            self.app_dir.mkdir(parents=True, exist_ok=True)

            # Count total files for progress calculation
            all_files = []
            for root_dir, _, filenames in os.walk(bundled_app_dir):
                for f in filenames:
                    all_files.append(Path(root_dir) / f)

            total_files = len(all_files) or 1
            copied_count = 0

            self._set_status("Installing application files...", 25)
            for item in os.listdir(bundled_app_dir):
                src_item = bundled_app_dir / item
                dst_item = self.app_dir / item
                if src_item.is_dir():
                    for s_root, _, s_files in os.walk(src_item):
                        rel_path = Path(s_root).relative_to(src_item)
                        target_sub = dst_item / rel_path
                        target_sub.mkdir(parents=True, exist_ok=True)
                        for sf in s_files:
                            src_file = Path(s_root) / sf
                            dst_file = target_sub / sf
                            shutil.copy2(src_file, dst_file)
                            copied_count += 1
                            pct = 25 + (copied_count / total_files) * 55
                            if copied_count % 10 == 0 or copied_count == total_files:
                                self._set_status("Copying application components...", pct, f"Copying: {sf}")
                else:
                    shutil.copy2(src_item, dst_item)
                    copied_count += 1

            self._set_status("Creating Desktop & Start Menu shortcuts...", 88)
            desktop_dir = get_special_folder("Desktop")
            programs_dir = get_special_folder("Programs")

            icon_path = self.app_dir / "_internal" / "assets" / "logo.ico"
            if not icon_path.exists():
                icon_path = self.app_dir / "assets" / "logo.ico"
            if not icon_path.exists():
                icon_path = self.app_exe

            # 1. Desktop shortcut
            desktop_shortcut = desktop_dir / "Result Analyzer.lnk"
            create_windows_shortcut(str(self.app_exe), str(desktop_shortcut), str(icon_path))

            # 2. Start menu shortcut
            programs_dir.mkdir(parents=True, exist_ok=True)
            start_menu_shortcut = programs_dir / "Result Analyzer.lnk"
            create_windows_shortcut(str(self.app_exe), str(start_menu_shortcut), str(icon_path))

            self._set_status("Finalizing installation...", 98)
            time.sleep(0.3)

            # Installation finished!
            self.root.after(0, self._on_install_complete)

        except Exception as err:
            self.root.after(0, lambda: self._on_install_error(str(err)))

    def _on_install_complete(self):
        self.status_lbl.config(text="✓  Installation Complete!", fg="#10b981", font=("Segoe UI", 11, "bold"))
        self.progress["value"] = 100
        self.detail_lbl.config(text=f"Shortcuts created on Desktop and in Start Menu.", fg="#94a3b8")

        # Replace buttons
        self.cancel_btn.pack_forget()

        launch_btn = tk.Button(self.btn_frame, text="Launch Result Analyzer", font=("Segoe UI", 9, "bold"),
                               bg="#ea2839", fg="#ffffff", activebackground="#cf1b2c",
                               activeforeground="#ffffff", relief="flat", padx=16, pady=4,
                               command=self._launch_and_close)
        launch_btn.pack(side="right", padx=(8, 0))

        close_btn = tk.Button(self.btn_frame, text="Finish", font=("Segoe UI", 9),
                              bg="#1e293b", fg="#cbd5e1", activebackground="#334155",
                              activeforeground="#ffffff", relief="flat", width=10, pady=4,
                              command=self.root.destroy)
        close_btn.pack(side="right")

    def _launch_and_close(self):
        try:
            if self.app_exe.exists():
                subprocess.Popen([str(self.app_exe)], cwd=str(self.app_dir))
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch application:\n{e}", parent=self.root)
        self.root.destroy()

    def _on_install_error(self, err_msg: str):
        self.status_lbl.config(text="✕  Installation Failed", fg="#ef4444", font=("Segoe UI", 11, "bold"))
        self.detail_lbl.config(text=err_msg, fg="#ef4444")
        messagebox.showerror("Installation Error", f"Installation could not be completed:\n\n{err_msg}", parent=self.root)


def main():
    root = tk.Tk()
    app = InstallerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
