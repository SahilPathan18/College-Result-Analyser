import os
import sys
import shutil
import subprocess

def create_shortcut(target, shortcut_path):
    ps_script = f"""
    $WshShell = New-Object -comObject WScript.Shell
    $Shortcut = $WshShell.CreateShortcut('{shortcut_path}')
    $Shortcut.TargetPath = '{target}'
    $Shortcut.WorkingDirectory = '{os.path.dirname(target)}'
    $Shortcut.Save()
    """
    subprocess.run(["powershell", "-Command", ps_script], capture_output=True)

def install():
    import tkinter as tk
    from tkinter import messagebox
    
    app_dir = os.path.join(os.environ['LOCALAPPDATA'], 'ResultAnalyzer')
    
    # Remove old installation if exists to avoid conflicts
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir, ignore_errors=True)
    os.makedirs(app_dir, exist_ok=True)
    
    app_exe = os.path.join(app_dir, 'ResultAnalyzer.exe')
    
    # When bundled, files are in sys._MEIPASS
    meipass = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    bundled_app_dir = os.path.join(meipass, 'ResultAnalyzer')
    
    if os.path.exists(bundled_app_dir):
        # Copy directory contents to app_dir
        for item in os.listdir(bundled_app_dir):
            s = os.path.join(bundled_app_dir, item)
            d = os.path.join(app_dir, item)
            if os.path.isdir(s):
                shutil.copytree(s, d, dirs_exist_ok=True)
            else:
                shutil.copy2(s, d)
        
        # Desktop shortcut
        desktop = os.path.join(os.environ['USERPROFILE'], 'Desktop')
        shortcut_path = os.path.join(desktop, 'Result Analyzer.lnk')
        create_shortcut(app_exe, shortcut_path)
        
        # Start menu shortcut
        start_menu = os.path.join(os.environ['APPDATA'], r'Microsoft\Windows\Start Menu\Programs')
        start_menu_shortcut = os.path.join(start_menu, 'Result Analyzer.lnk')
        create_shortcut(app_exe, start_menu_shortcut)
        
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("Installation Complete", "Result Analyzer has been installed successfully!\n\n(It will now launch much faster because it does not need to extract dependencies every time!)\n\nYou can now launch it from your Desktop or Start Menu.")
    else:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", "Installation failed: Application bundle not found.")

if __name__ == '__main__':
    install()
