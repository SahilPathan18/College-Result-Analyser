"""
Main entry point for Bangalore University Result Analyzer.
"""
from __future__ import annotations

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))


def main() -> None:
    from ui.main_window import MainWindow
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
