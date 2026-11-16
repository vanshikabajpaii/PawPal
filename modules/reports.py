"""
PawPal - Reports & Analytics Module
Displays charts and statistics about pets, adoptions, and vaccinations.
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import sys
import os

# Matplotlib imports
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import database as db

# ── Color palette ────────────────────────────────────────────────────────────
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

# Try to use a nice style; fall back gracefully
try:
    plt.style.use("seaborn-v0_8-pastel")
except OSError:
    try:
        plt.style.use("seaborn-pastel")
    except OSError:
        pass  # use matplotlib default


class ReportsModule(tk.Frame):
    """Reports & Analytics page — four charts + summary statistics."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)

        # Keep references to canvas objects so we can destroy/redraw them
        self._canvases = []
        self._figures  = []

        self._build_ui()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_ui(self):
        """Build the full page layout."""
        self._build_header()
        self._build_charts_area()
        self._build_stats_table()

    def _build_header(self):
        """Page title + Refresh button row."""
        header = tk.Frame(self, bg=BG_COLOR)
        header.pack(fill=tk.X, padx=10, pady=(10, 5))

        tk.Label(
            header,
            text="📊  Reports & Analytics",
            font=("Segoe UI", 20, "bold"),
            bg=BG_COLOR,
            fg=DARK_TEXT,
        ).pack(side=tk.LEFT)

        tk.Button(
            header,
            text="🔄  Refresh Reports",
            font=("Segoe UI", 10, "bold"),
            bg=CORAL,
            fg=DARK_TEXT,
            activebackground="#f4a08a",
            relief="flat",
            padx=14,
            pady=6,
            cursor="hand2",
            command=self.refresh,
        ).pack(side=tk.RIGHT, padx=5)

    def _build_charts_area(self):
        """2×2 grid of matplotlib charts inside a scrollable canvas."""
        # Outer container that will hold the 2×2 grid
        self.charts_container = tk.Frame(self, bg=BG_COLOR)
        self.charts_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        # We'll populate charts in refresh()

    def _build_stats_table(self):
        """Summary statistics row at the bottom."""
        outer = tk.Frame(self, bg=BG_COLOR)
        outer.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Section label
        tk.Label(
            outer,
            text="Summary Statistics",
            font=("Segoe UI", 13, "bold"),
            bg=BG_COLOR,
            fg=DARK_TEXT,
        ).pack(anchor="w", pady=(0, 6))

        self.stats_frame = tk.Frame(outer, bg=WHITE, bd=1, relief="solid")
        self.stats_frame.pack(fill=tk.X)

        # Placeholder — populated in _refresh_stats()
        self._stat_labels = {}
        stat_defs = [
            ("total_pets",        "Total Pets Registered"),
            ("available",         "Currently Available"),
            ("adopted",           "Successfully Adopted"),
            ("pending",           "Pending Applications"),
            ("total_vaccinations","Total Vaccinations Recorded"),
            ("upcoming_vacc",     "Upcoming Vaccinations (next 30 days)"),
        ]

        for col, (key, label) in enumerate(stat_defs):
            cell = tk.Frame(self.stats_frame, bg=WHITE, padx=18, pady=12)
            cell.grid(row=0, column=col, sticky="nsew", padx=1, pady=1)
            self.stats_frame.columnconfigure(col, weight=1)

            tk.Label(
                cell,
                text=label,
                font=("Segoe UI", 9),
                bg=WHITE,
                fg=DARK_TEXT,
                wraplength=100,
                justify="center",
            ).pack()

            val_lbl = tk.Label(
                cell,
                text="–",
                font=("Segoe UI", 22, "bold"),
                bg=WHITE,
                fg=CORAL,
            )
            val_lbl.pack(pady=(4, 0))
            self._stat_labels[key] = val_lbl

    # ── Refresh / data loading ───────────────────────────────────────────────

    def refresh(self):
        """Reload all charts and statistics from the database."""
        self._clear_charts()
        self._draw_all_charts()
        self._refresh_stats()

    def _clear_charts(self):
        """Destroy existing chart widgets and close figures."""
        for canvas in self._canvases:
            canvas.get_tk_widget().destroy()
        for fig in self._figures:
            plt.close(fig)
        self._canvases.clear()
        self._figures.clear()

        # Destroy and recreate the charts container so grid is clean
        self.charts_container.destroy()
        self.charts_container = tk.Frame(self, bg=BG_COLOR)
        # Insert it between header and stats — use place_configure trick with pack
        # We use pack order; rebuild between existing widgets by repacking
        # Easiest: destroy & recreate the whole layout isn't ideal,
        # so we simply re-pack the container before stats_frame's parent
        self.charts_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5,
                                   before=self._stats_outer_ref())

    def _stats_outer_ref(self):
        """Return the stats outer frame widget (the last child of self)."""
        children = self.pack_slaves()
        # The last packed widget is the stats outer frame
        if len(children) >= 1:
            return children[-1]
        return None

    def _draw_all_charts(self):
        """Draw all four charts into the charts_container grid."""
        container = self.charts_container

        # Row/col configuration
        for r in range(2):
            container.rowconfigure(r, weight=1)
        for c in range(2):
            container.columnconfigure(c, weight=1)

        # Fetch data once
        pets         = db.get_all_pets()
        adoptions    = db.get_all_applications()
        vaccinations = db.get_all_vaccinations()

        # 1. Species Distribution (top-left)
        fig1, ax1 = plt.subplots(figsize=(5, 3.5))
        self._chart_species_pie(ax1, pets)
        self._embed_chart(fig1, container, row=0, col=0, title="Species Distribution")

        # 2. Adoption Status Overview (top-right)
        fig2, ax2 = plt.subplots(figsize=(5, 3.5))
        self._chart_adoption_donut(ax2, pets)
        self._embed_chart(fig2, container, row=0, col=1, title="Adoption Status Overview")

        # 3. Monthly Adoptions (bottom-left)
        fig3, ax3 = plt.subplots(figsize=(5, 3.5))
        self._chart_monthly_adoptions(ax3, adoptions)
        self._embed_chart(fig3, container, row=1, col=0, title="Monthly Adoptions (Last 6 Months)")

        # 4. Vaccination Summary (bottom-right)
        fig4, ax4 = plt.subplots(figsize=(5, 3.5))
        self._chart_vaccination_summary(ax4, vaccinations)
        self._embed_chart(fig4, container, row=1, col=1, title="Vaccination Summary")

    # ── Individual chart builders ────────────────────────────────────────────

    def _chart_species_pie(self, ax, pets):
        """Pie chart: count of each species."""
        from collections import Counter
        species_counts = Counter(p.get("species", "Unknown") for p in pets)

        if not species_counts:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color=DARK_TEXT)
            ax.axis("off")
            return

        labels = list(species_counts.keys())
        sizes  = list(species_counts.values())

        pastel_colors = [
            "#F7B8A5",  # coral
            "#B8E0D2",  # mint
            "#D8C8F0",  # lavender
            "#FFF0C2",  # yellow
            "#AED6F1",  # light blue
            "#F9C8D8",  # light pink
            "#C8F9E0",  # light green
            "#FAD7A0",  # peach
        ]
        colors = pastel_colors[:len(labels)]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct="%1.1f%%",
            colors=colors,
            startangle=140,
            pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 1.5},
        )
        for at in autotexts:
            at.set_fontsize(8)
            at.set_color(DARK_TEXT)

        ax.legend(
            wedges, labels,
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=8,
            frameon=False,
        )
        ax.set_title("", pad=0)

    def _chart_adoption_donut(self, ax, pets):
        """Donut chart: Available / Adopted / Pending."""
        from collections import Counter
        status_counts = Counter(p.get("status", "Unknown") for p in pets)

        available = status_counts.get("Available", 0)
        adopted   = status_counts.get("Adopted", 0)
        pending   = status_counts.get("Pending", 0)

        labels = ["Available", "Adopted", "Pending"]
        sizes  = [available, adopted, pending]
        colors = [SUCCESS_COLOR, CORAL, YELLOW]

        # Filter zeros
        filtered = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
        if not filtered:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color=DARK_TEXT)
            ax.axis("off")
            return

        labels_f  = [f[0] for f in filtered]
        sizes_f   = [f[1] for f in filtered]
        colors_f  = [f[2] for f in filtered]

        wedges, texts, autotexts = ax.pie(
            sizes_f,
            labels=None,
            autopct="%1.1f%%",
            colors=colors_f,
            startangle=90,
            pctdistance=0.75,
            wedgeprops={"edgecolor": "white", "linewidth": 2, "width": 0.55},
        )
        for at in autotexts:
            at.set_fontsize(9)
            at.set_color(DARK_TEXT)

        ax.legend(
            wedges,
            [f"{l} ({s})" for l, s in zip(labels_f, sizes_f)],
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=9,
            frameon=False,
        )

    def _chart_monthly_adoptions(self, ax, adoptions):
        """Bar chart: adoptions per month for the last 6 months."""
        from collections import defaultdict

        now    = datetime.now()
        months = []
        for i in range(5, -1, -1):
            m = now.month - i
            y = now.year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))

        month_names = {
            1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr",
            5: "May", 6: "Jun", 7: "Jul", 8: "Aug",
            9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
        }

        counts = defaultdict(int)
        for adoption in adoptions:
            status = adoption.get("status", "")
            if status != "Approved":
                continue
            date_str = adoption.get("adoption_date") or adoption.get("application_date", "")
            if not date_str:
                continue
            try:
                # Support both date formats
                for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
                    try:
                        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
                        break
                    except ValueError:
                        continue
                else:
                    continue
                counts[(d.year, d.month)] += 1
            except Exception:
                continue

        x_labels = [month_names[m] for _, m in months]
        y_values  = [counts[(y, m)] for y, m in months]

        bars = ax.bar(x_labels, y_values, color=CORAL, edgecolor="white", linewidth=1.2)

        # Value labels on top of each bar
        for bar, val in zip(bars, y_values):
            if val > 0:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.1,
                    str(val),
                    ha="center", va="bottom",
                    fontsize=9, color=DARK_TEXT, fontweight="bold",
                )

        ax.set_xlabel("Month", fontsize=9, color=DARK_TEXT)
        ax.set_ylabel("Adoptions", fontsize=9, color=DARK_TEXT)
        ax.set_ylim(0, max(y_values + [1]) + 2)
        ax.tick_params(axis="both", labelsize=8, colors=DARK_TEXT)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor(BG_COLOR)

    def _chart_vaccination_summary(self, ax, vaccinations):
        """Horizontal bar chart: top 5 most common vaccine names."""
        from collections import Counter

        vacc_counts = Counter(v.get("vaccine_name", "Unknown") for v in vaccinations)

        if not vacc_counts:
            ax.text(0.5, 0.5, "No data", ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color=DARK_TEXT)
            ax.axis("off")
            return

        top5 = vacc_counts.most_common(5)
        labels = [item[0] for item in reversed(top5)]
        values = [item[1] for item in reversed(top5)]

        bars = ax.barh(labels, values, color=MINT, edgecolor="white", linewidth=1.2)

        for bar, val in zip(bars, values):
            ax.text(
                bar.get_width() + 0.1,
                bar.get_y() + bar.get_height() / 2,
                str(val),
                va="center", ha="left",
                fontsize=9, color=DARK_TEXT, fontweight="bold",
            )

        ax.set_xlabel("Count", fontsize=9, color=DARK_TEXT)
        ax.set_xlim(0, max(values) + max(values) * 0.2 + 1)
        ax.tick_params(axis="both", labelsize=8, colors=DARK_TEXT)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_facecolor(BG_COLOR)

    # ── Chart embedding helper ───────────────────────────────────────────────

    def _embed_chart(self, fig, container, row, col, title=""):
        """Embed a matplotlib figure into the tkinter grid container."""
        fig.patch.set_facecolor(BG_COLOR)
        fig.tight_layout(pad=1.5)

        cell = tk.Frame(container, bg=WHITE, bd=1, relief="solid")
        cell.grid(row=row, column=col, sticky="nsew", padx=5, pady=5)

        # Chart title label
        tk.Label(
            cell,
            text=title,
            font=("Segoe UI", 10, "bold"),
            bg=WHITE,
            fg=DARK_TEXT,
            pady=4,
        ).pack(fill=tk.X, padx=8)

        canvas = FigureCanvasTkAgg(fig, master=cell)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

        self._canvases.append(canvas)
        self._figures.append(fig)

    # ── Statistics refresh ───────────────────────────────────────────────────

    def _refresh_stats(self):
        """Populate the summary statistics labels from the database."""
        try:
            stats = db.get_dashboard_stats()
        except Exception:
            stats = {}

        # Total vaccinations count (not in dashboard_stats, so fetch separately)
        try:
            all_vaccinations = db.get_all_vaccinations()
            total_vaccinations = len(all_vaccinations)
        except Exception:
            all_vaccinations = []
            total_vaccinations = 0

        # Upcoming vaccinations in next 30 days
        try:
            vaccinations = all_vaccinations if all_vaccinations else db.get_all_vaccinations()
            today     = datetime.now().date()
            threshold = today + timedelta(days=30)
            upcoming = sum(
                1 for v in vaccinations
                if v.get("next_due_date") and self._parse_date(v["next_due_date"]) and
                   today <= self._parse_date(v["next_due_date"]) <= threshold
            )
        except Exception:
            upcoming = 0

        mapping = {
            "total_pets":         stats.get("total_pets", 0),
            "available":          stats.get("available_pets", 0),
            "adopted":            stats.get("adopted_pets", 0),
            "pending":            stats.get("pending_applications", 0),
            "total_vaccinations": total_vaccinations,
            "upcoming_vacc":      upcoming,
        }
        for key, value in mapping.items():
            if key in self._stat_labels:
                self._stat_labels[key].config(text=str(value))

    @staticmethod
    def _parse_date(date_str):
        """Parse a date string into a date object; return None on failure."""
        for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(date_str[:10], "%Y-%m-%d").date()
            except (ValueError, TypeError):
                continue
        return None
