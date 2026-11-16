"""
ui/sidebar.py — PawPal sidebar navigation component.

The Sidebar is a fixed-width vertical panel containing:
  • App logo / branding area
  • Navigation items (icon + label)
  • Version / credits footer

Usage
-----
    sidebar = Sidebar(root, navigate_callback=on_navigate)
    sidebar.pack(side=tk.LEFT, fill=tk.Y)
    sidebar.set_active("dashboard")
"""

import tkinter as tk

from ui.theme import (
    SIDEBAR_BG, SIDEBAR_TEXT, SIDEBAR_ACTIVE, CORAL,
    FONT_SIDEBAR, FONT_SIDEBAR_HEADER, FONT_SMALL,
    PADDING,
)

# ---------------------------------------------------------------------------
# Navigation items: (icon, human-readable label, module_name)
# ---------------------------------------------------------------------------
_NAV_ITEMS = [
    ("🏠", "Dashboard",    "dashboard"),
    ("🐾", "Pets",         "pets"),
    ("❤️",  "Adoptions",   "adoptions"),
    ("💉", "Vaccinations", "vaccinations"),
    ("📊", "Reports",      "reports"),
]

_SIDEBAR_WIDTH = 220   # pixels


class Sidebar(tk.Frame):
    """
    Collapsible sidebar navigation for PawPal.

    Parameters
    ----------
    parent            : tk widget — parent container
    navigate_callback : callable — called with module_name (str) on click
    **kwargs          : forwarded to tk.Frame
    """

    def __init__(self, parent, navigate_callback=None, **kwargs):
        super().__init__(
            parent,
            bg=SIDEBAR_BG,
            width=_SIDEBAR_WIDTH,
            **kwargs,
        )
        # Prevent the frame from shrinking to fit its children
        self.pack_propagate(False)

        self._navigate = navigate_callback
        self._active   = None           # currently active module_name
        self._nav_frames: dict[str, tk.Frame] = {}   # module_name → Frame

        self._build_logo()
        self._build_separator()
        self._build_nav()
        self._build_footer()

    # -----------------------------------------------------------------------
    # Build helpers
    # -----------------------------------------------------------------------

    def _build_logo(self):
        """App branding area at the top of the sidebar."""
        logo_frame = tk.Frame(self, bg=SIDEBAR_BG,
                              pady=PADDING["xlarge"])
        logo_frame.pack(fill=tk.X)

        # Paw icon + app name
        tk.Label(
            logo_frame,
            text="🐾",
            font=("Segoe UI", 32),
            bg=SIDEBAR_BG,
            fg=CORAL,
        ).pack()

        tk.Label(
            logo_frame,
            text="PawPal",
            font=FONT_SIDEBAR_HEADER,
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
        ).pack()

        tk.Label(
            logo_frame,
            text="Pet Management",
            font=FONT_SMALL,
            bg=SIDEBAR_BG,
            fg="#A0ACBA",
        ).pack()

    # ------------------------------------------------------------------
    def _build_separator(self):
        """Thin horizontal rule under the logo."""
        tk.Frame(self, bg="#4E5B6B", height=1).pack(fill=tk.X,
                                                     padx=PADDING["medium"],
                                                     pady=PADDING["small"])

    # ------------------------------------------------------------------
    def _build_nav(self):
        """Create a clickable row for each navigation item."""
        nav_container = tk.Frame(self, bg=SIDEBAR_BG)
        nav_container.pack(fill=tk.X, pady=PADDING["small"])

        for icon, label, module_name in _NAV_ITEMS:
            self._create_nav_item(nav_container, icon, label, module_name)

    # ------------------------------------------------------------------
    def _create_nav_item(self, parent, icon: str, label: str,
                         module_name: str):
        """Build a single nav row and register it in self._nav_frames."""
        row = tk.Frame(parent, bg=SIDEBAR_BG, cursor="hand2")
        row.pack(fill=tk.X, pady=1)

        icon_lbl = tk.Label(
            row,
            text=icon,
            font=("Segoe UI", 15),
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
            padx=PADDING["large"],
            pady=PADDING["medium"],
        )
        icon_lbl.pack(side=tk.LEFT)

        text_lbl = tk.Label(
            row,
            text=label,
            font=FONT_SIDEBAR,
            bg=SIDEBAR_BG,
            fg=SIDEBAR_TEXT,
            anchor="w",
            pady=PADDING["medium"],
        )
        text_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Store reference
        self._nav_frames[module_name] = row

        # Bind click on the row and both child labels
        for widget in (row, icon_lbl, text_lbl):
            widget.bind("<Button-1>",
                        lambda _e, m=module_name: self._on_click(m))
            widget.bind("<Enter>",
                        lambda _e, r=row, m=module_name: self._on_enter(r, m))
            widget.bind("<Leave>",
                        lambda _e, r=row, m=module_name: self._on_leave(r, m))

    # ------------------------------------------------------------------
    def _build_footer(self):
        """Version and credits pushed to the bottom of the sidebar."""
        tk.Frame(self, bg=SIDEBAR_BG).pack(fill=tk.BOTH, expand=True)

        separator = tk.Frame(self, bg="#4E5B6B", height=1)
        separator.pack(fill=tk.X, padx=PADDING["medium"],
                       pady=(PADDING["small"], 0))

        footer = tk.Frame(self, bg=SIDEBAR_BG, pady=PADDING["medium"])
        footer.pack(fill=tk.X)

        tk.Label(
            footer,
            text="v1.0.0",
            font=FONT_SMALL,
            bg=SIDEBAR_BG,
            fg="#6B7A8D",
        ).pack()

        tk.Label(
            footer,
            text="© 2024 PawPal",
            font=FONT_SMALL,
            bg=SIDEBAR_BG,
            fg="#6B7A8D",
        ).pack()

    # -----------------------------------------------------------------------
    # Hover / click handlers
    # -----------------------------------------------------------------------

    def _on_enter(self, row: tk.Frame, module_name: str):
        """Highlight row on hover — but don't override the active item."""
        if module_name != self._active:
            self._set_row_color(row, SIDEBAR_ACTIVE, SIDEBAR_BG)

    def _on_leave(self, row: tk.Frame, module_name: str):
        """Restore normal colours — but don't clear the active item."""
        if module_name != self._active:
            self._set_row_color(row, SIDEBAR_BG, SIDEBAR_TEXT)

    def _on_click(self, module_name: str):
        """Navigate to module_name and update the active highlight."""
        self.set_active(module_name)
        if self._navigate:
            self._navigate(module_name)

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    def set_active(self, module_name: str):
        """
        Highlight *module_name* as the active section and
        restore the previously active item to its default style.
        """
        # Deactivate previous
        if self._active and self._active in self._nav_frames:
            prev = self._nav_frames[self._active]
            self._set_row_color(prev, SIDEBAR_BG, SIDEBAR_TEXT)

        self._active = module_name

        # Activate new
        if module_name in self._nav_frames:
            row = self._nav_frames[module_name]
            self._set_row_color(row, SIDEBAR_ACTIVE, SIDEBAR_BG)

    # -----------------------------------------------------------------------
    # Internal utilities
    # -----------------------------------------------------------------------

    @staticmethod
    def _set_row_color(row: tk.Frame, bg: str, fg: str):
        """Recursively apply bg/fg to a nav row and its child labels."""
        row.config(bg=bg)
        for child in row.winfo_children():
            try:
                child.config(bg=bg, fg=fg)
            except tk.TclError:
                pass
