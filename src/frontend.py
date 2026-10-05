"""
Frontend module for Bangalore University Result Analyzer.
Exposes the modern CustomTkinter MainWindow.
"""
from __future__ import annotations

from ui.main_window import MainWindow

# Backward-compatible alias for existing scripts and tests
ResultAnalyzerApp = MainWindow

__all__ = ["ResultAnalyzerApp", "MainWindow"]
