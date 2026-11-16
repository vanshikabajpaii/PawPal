"""
PawPal - Dashboard Module
Displays overview stats, recent pets, species distribution pie chart,
and monthly adoptions bar chart.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime

try:
    import matplotlib
    matplotlib.use("TkAgg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import database as db
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ── Colour palette ──────────────────────────────────────────────────────────
BG_COLOR         = "#FFF9F2"
CORAL            = "#F7B8A5"
MINT             = "#B8E0D2"
LAVENDER         = "#D8C8F0"
YELLOW           = "#FFF0C2"
DARK_TEXT        = "#39434F"
WHITE            = "#FFFFFF"
SIDEBAR_BG       = "#39434F"
SUCCESS_COLOR    = "#4CAF50"
ERROR_COLOR      = "#F44336"
TABLE_HEADER_BG  = "#39434F"
TABLE_HEADER_FG  = "#FFFFFF"
TABLE_ROW_ODD    = "#FFF9F2"
TABLE_ROW_EVEN   = "#F5F0EA"
BORDER_COLOR     = "#E0D8D0"


class DashboardModule(tk.Frame):
    """Main dashboard frame shown on the PawPal home screen."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", BG_COLOR)
        super().__init__(parent, **kwargs)

        # Canvas holders so we can destroy/recreate charts on refresh
        self._pie_canvas  = None
        self._bar_canvas  = None

        # Stat-card value labels — filled in refresh()
        self._stat_labels = {}

        self._build_ui()
        self.refresh()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        # Allow the frame to expand
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)   # middle section grows
        self.rowconfigure(3, weight=1)   # bottom section grows

        self._build_header()
        self._build_stats_row()
        self._build_middle_section()
        self._build_bottom_section()

    def _build_header(self):
        header = tk.Frame(self, bg=BG_COLOR)
        header.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 4))

        tk.Label(
            header,
            text="Dashboard",
            font=("Segoe UI", 26, "bold"),
            bg=BG_COLOR,
            fg=DARK_TEXT,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Welcome to PawPal - Pet Adoption & Care Management",
            font=("Segoe UI", 12),
            bg=BG_COLOR,
            fg="#6B7A8D",
        ).pack(anchor="w")

    def _build_stats_row(self):
        stats_frame = tk.Frame(self, bg=BG_COLOR)
        stats_frame.grid(row=1, column=0, sticky="ew", padx=24, pady=12)
        for i in range(4):
            stats_frame.columnconfigure(i, weight=1)

        cards = [
            ("total_pets",         "🐾", "Total Pets",             CORAL),
            ("available_pets",     "✅", "Available Pets",          MINT),
            ("adopted_pets",       "🏠", "Adopted Pets",            LAVENDER),
            ("pending_apps",       "⏳", "Pending Applications",    YELLOW),
        ]

        for col, (key, icon, label, color) in enumerate(cards):
            card = tk.Frame(stats_frame, bg=color, padx=20, pady=16,
                            relief="flat", bd=0)
            card.grid(row=0, column=col, padx=8, pady=4, sticky="ew")

            tk.Label(card, text=icon, font=("Segoe UI", 28),
                     bg=color, fg=DARK_TEXT).pack(anchor="w")

            num_lbl = tk.Label(card, text="—", font=("Segoe UI", 32, "bold"),
                               bg=color, fg=DARK_TEXT)
            num_lbl.pack(anchor="w")
            self._stat_labels[key] = num_lbl

            tk.Label(card, text=label, font=("Segoe UI", 11),
                     bg=color, fg=DARK_TEXT).pack(anchor="w")

    def _build_middle_section(self):
        mid = tk.Frame(self, bg=BG_COLOR)
        mid.grid(row=2, column=0, sticky="nsew", padx=24, pady=8)
        mid.columnconfigure(0, weight=3)
        mid.columnconfigure(1, weight=2)
        mid.rowconfigure(0, weight=1)

        # ── Left: Recent Pets ──────────────────────────────────────────────
        left = tk.Frame(mid, bg=WHITE, relief="flat", bd=1)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        tk.Label(left, text="Recently Registered Pets",
                 font=("Segoe UI", 13, "bold"),
                 bg=WHITE, fg=DARK_TEXT, pady=10).grid(
            row=0, column=0, sticky="w", padx=14)

        # Treeview
        tree_frame = tk.Frame(left, bg=WHITE)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        cols = ("Name", "Species", "Status", "Date")
        self.recent_tree = ttk.Treeview(tree_frame, columns=cols,
                                        show="headings", height=6)
        for col in cols:
            self.recent_tree.heading(col, text=col)
            self.recent_tree.column(col, width=100, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self.recent_tree.yview)
        self.recent_tree.configure(yscrollcommand=vsb.set)
        self.recent_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._style_treeview()

        # ── Right: Pie Chart ───────────────────────────────────────────────
        self.pie_frame = tk.Frame(mid, bg=WHITE, relief="flat", bd=1)
        self.pie_frame.grid(row=0, column=1, sticky="nsew")
        self.pie_frame.rowconfigure(1, weight=1)
        self.pie_frame.columnconfigure(0, weight=1)

        tk.Label(self.pie_frame, text="Species Distribution",
                 font=("Segoe UI", 13, "bold"),
                 bg=WHITE, fg=DARK_TEXT, pady=10).grid(
            row=0, column=0, sticky="w", padx=14)

        self.pie_chart_area = tk.Frame(self.pie_frame, bg=WHITE)
        self.pie_chart_area.grid(row=1, column=0, sticky="nsew",
                                 padx=10, pady=(0, 10))

    def _build_bottom_section(self):
        bot = tk.Frame(self, bg=WHITE, relief="flat", bd=1)
        bot.grid(row=3, column=0, sticky="nsew", padx=24, pady=(8, 24))
        bot.rowconfigure(1, weight=1)
        bot.columnconfigure(0, weight=1)

        tk.Label(bot, text="Monthly Adoptions",
                 font=("Segoe UI", 13, "bold"),
                 bg=WHITE, fg=DARK_TEXT, pady=10).grid(
            row=0, column=0, sticky="w", padx=14)

        self.bar_chart_area = tk.Frame(bot, bg=WHITE)
        self.bar_chart_area.grid(row=1, column=0, sticky="nsew",
                                 padx=10, pady=(0, 10))

    # ── Treeview styling ─────────────────────────────────────────────────────

    def _style_treeview(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dashboard.Treeview",
                        background=TABLE_ROW_ODD,
                        foreground=DARK_TEXT,
                        rowheight=28,
                        fieldbackground=TABLE_ROW_ODD,
                        font=("Segoe UI", 10))
        style.configure("Dashboard.Treeview.Heading",
                        background=TABLE_HEADER_BG,
                        foreground=TABLE_HEADER_FG,
                        font=("Segoe UI", 10, "bold"))
        style.map("Dashboard.Treeview",
                  background=[("selected", CORAL)])
        self.recent_tree.configure(style="Dashboard.Treeview")
        self.recent_tree.tag_configure("odd",  background=TABLE_ROW_ODD)
        self.recent_tree.tag_configure("even", background=TABLE_ROW_EVEN)

    # ── Chart creation ───────────────────────────────────────────────────────

    def create_pie_chart(self, frame, species_data):
        """Create a matplotlib pie chart and return FigureCanvasTkAgg."""
        fig, ax = plt.subplots(figsize=(3.6, 2.8), facecolor=WHITE)
        ax.set_facecolor(WHITE)

        if not species_data:
            ax.text(0.5, 0.5, "No data available",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color=DARK_TEXT)
            ax.axis("off")
        else:
            labels = [row[0] or "Unknown" for row in species_data]
            sizes  = [row[1] for row in species_data]
            colors = [CORAL, MINT, LAVENDER, YELLOW,
                      "#A8D8EA", "#FFAAA5", "#D4E157"][:len(labels)]

            wedges, texts, autotexts = ax.pie(
                sizes, labels=labels, colors=colors,
                autopct="%1.0f%%", startangle=90,
                wedgeprops=dict(edgecolor=WHITE, linewidth=2),
                textprops=dict(color=DARK_TEXT, fontsize=8),
            )
            for at in autotexts:
                at.set_fontsize(8)

        fig.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        return canvas

    def create_bar_chart(self, frame, monthly_data):
        """Create a matplotlib bar chart and return FigureCanvasTkAgg."""
        fig, ax = plt.subplots(figsize=(7, 2.8), facecolor=WHITE)
        ax.set_facecolor("#FAFAFA")

        if not monthly_data:
            ax.text(0.5, 0.5, "No data available",
                    ha="center", va="center", transform=ax.transAxes,
                    fontsize=10, color=DARK_TEXT)
            ax.axis("off")
        else:
            months = [row[0] for row in monthly_data]
            counts = [row[1] for row in monthly_data]

            bars = ax.bar(months, counts, color=CORAL, edgecolor=WHITE,
                          linewidth=1.5, width=0.5)
            for bar, count in zip(bars, counts):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.1,
                        str(count), ha="center", va="bottom",
                        fontsize=9, color=DARK_TEXT)

            ax.set_ylabel("Adoptions", fontsize=9, color=DARK_TEXT)
            ax.set_xlabel("Month", fontsize=9, color=DARK_TEXT)
            ax.tick_params(axis="both", labelsize=8, colors=DARK_TEXT)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.set_ylim(0, max(counts) + max(1, max(counts) * 0.2))

        fig.tight_layout(pad=0.8)
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        return canvas

    # ── Refresh ──────────────────────────────────────────────────────────────

    def refresh(self):
        """Reload all data from the database and redraw every widget."""
        stats        = self._fetch_stats()
        recent_pets  = self._fetch_recent_pets()
        species_data = self._fetch_species_data()
        monthly_data = self._fetch_monthly_data()

        # Update stat cards
        self._stat_labels["total_pets"].config(
            text=str(stats.get("total_pets", 0)))
        self._stat_labels["available_pets"].config(
            text=str(stats.get("available_pets", 0)))
        self._stat_labels["adopted_pets"].config(
            text=str(stats.get("adopted_pets", 0)))
        self._stat_labels["pending_apps"].config(
            text=str(stats.get("pending_applications", 0)))

        # Refresh recent pets treeview
        self.recent_tree.delete(*self.recent_tree.get_children())
        for idx, pet in enumerate(recent_pets):
            tag = "even" if idx % 2 == 0 else "odd"
            name    = pet.get("name") if hasattr(pet, "get") else (pet[1] if len(pet) > 1 else "—")
            species = pet.get("species") if hasattr(pet, "get") else (pet[2] if len(pet) > 2 else "—")
            status  = pet.get("status") if hasattr(pet, "get") else (pet[7] if len(pet) > 7 else "—")
            raw_dt  = pet.get("date_registered") if hasattr(pet, "get") else (pet[9] if len(pet) > 9 else "—")
            date    = str(raw_dt)[:10] if raw_dt else "—"
            self.recent_tree.insert("", "end",
                                    values=(name, species, status, date),
                                    tags=(tag,))

        # Redraw pie chart
        self._redraw_chart(
            area=self.pie_chart_area,
            canvas_attr="_pie_canvas",
            creator=self.create_pie_chart,
            data=species_data,
        )

        # Redraw bar chart
        self._redraw_chart(
            area=self.bar_chart_area,
            canvas_attr="_bar_canvas",
            creator=self.create_bar_chart,
            data=monthly_data,
        )

    def _redraw_chart(self, area, canvas_attr, creator, data):
        """Destroy old canvas widget and create a fresh one."""
        if not MATPLOTLIB_AVAILABLE:
            tk.Label(area, text="matplotlib not installed",
                     bg=WHITE, fg=ERROR_COLOR,
                     font=("Segoe UI", 10)).pack()
            return

        old_canvas = getattr(self, canvas_attr)
        if old_canvas is not None:
            try:
                old_canvas.get_tk_widget().destroy()
                plt.close("all")
            except Exception:
                pass

        canvas = creator(area, data)
        canvas.get_tk_widget().pack(fill="both", expand=True)
        setattr(self, canvas_attr, canvas)

    # ── Data fetching (with safe fallbacks) ──────────────────────────────────

    def _fetch_stats(self):
        if DB_AVAILABLE:
            try:
                return db.get_dashboard_stats()
            except Exception:
                pass
        return {
            "total_pets": 0,
            "available_pets": 0,
            "adopted_pets": 0,
            "pending_applications": 0,
        }

    def _fetch_recent_pets(self):
        if DB_AVAILABLE:
            try:
                return db.get_recent_pets(limit=5)
            except Exception:
                pass
        return []

    def _fetch_species_data(self):
        if DB_AVAILABLE:
            try:
                return db.get_species_distribution()
            except Exception:
                pass
        return []

    def _fetch_monthly_data(self):
        if DB_AVAILABLE:
            try:
                return db.get_monthly_adoptions(months=6)
            except Exception:
                pass
        return []
