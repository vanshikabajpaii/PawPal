"""
PawPal - Main Application Entry Point
Launches the PawPal Pet Adoption & Care Management System.
"""

import tkinter as tk
from tkinter import ttk
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import database as db
from ui.sidebar import Sidebar
from modules.dashboard import DashboardModule
from modules.pets import PetsModule
from modules.adoptions import AdoptionsModule
from modules.vaccinations import VaccinationsModule
from modules.reports import ReportsModule

# ── Color palette ─────────────────────────────────────────────────────────────
BG_COLOR = "#FFF9F2"


class PawPalApp(tk.Tk):
    """Root application window for PawPal."""

    def __init__(self):
        super().__init__()

        # ── Window setup ──────────────────────────────────────────────────────
        self.title("PawPal - Pet Adoption & Care Management System")
        self.minsize(1200, 700)
        self.configure(bg=BG_COLOR)

        # Maximise on Windows
        try:
            self.state("zoomed")
        except tk.TclError:
            # Non-Windows fallback
            self.attributes("-zoomed", True)

        # Optional window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                 "assets", "icons", "paw.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass  # Icon loading failed — not critical

        # ── Database initialisation ───────────────────────────────────────────
        db.initialize_database()
        db.seed_sample_data()

        # ── Layout: Sidebar (left, 220 px) + Content area (right) ────────────
        self._build_layout()

        # ── Initialise all modules ────────────────────────────────────────────
        self.modules = {
            "dashboard":    DashboardModule(self.content_frame),
            "pets":         PetsModule(self.content_frame),
            "adoptions":    AdoptionsModule(self.content_frame),
            "vaccinations": VaccinationsModule(self.content_frame),
            "reports":      ReportsModule(self.content_frame),
        }

        # ── Show dashboard on start ───────────────────────────────────────────
        self.current_module = None
        self.navigate("dashboard")

    # ── Layout construction ───────────────────────────────────────────────────

    def _build_layout(self):
        """Create sidebar and content area."""
        # Sidebar — fixed 220 px wide, full height
        self.sidebar = Sidebar(self, navigate_callback=self.navigate)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Content area — takes all remaining space
        self.content_frame = tk.Frame(self, bg=BG_COLOR, padx=20, pady=20)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # ── Navigation ────────────────────────────────────────────────────────────

    def navigate(self, module_name: str):
        """Switch to a named module, hiding all others."""
        # Hide every module
        for frame in self.modules.values():
            frame.pack_forget()

        # Show the requested module
        target = self.modules.get(module_name)
        if target is None:
            return

        target.pack(fill=tk.BOTH, expand=True)

        # Refresh data if the module supports it
        if hasattr(target, "refresh") and callable(target.refresh):
            target.refresh()

        # Update sidebar highlight
        if hasattr(self.sidebar, "set_active"):
            self.sidebar.set_active(module_name)

        self.current_module = module_name


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    app = PawPalApp()
    app.mainloop()
