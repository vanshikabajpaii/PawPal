"""
vaccinations.py — Vaccinations Module for PawPal
Handles vaccination records, status tracking, and upcoming-due alerts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime, timedelta

import database as db

# ── Palette ────────────────────────────────────────────────────────────────────
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

FONT             = "Segoe UI"

COMMON_VACCINES  = [
    "Rabies", "Distemper", "Parvovirus", "Bordetella",
    "FVRCP", "FeLV", "Leptospirosis", "Lyme Disease",
    "Adenovirus", "Parainfluenza",
]

DATE_FMT = "%d-%m-%Y"


# ── Helpers ────────────────────────────────────────────────────────────────────
def _parse_date(text):
    """Parse a DD-MM-YYYY string; return a date object or None."""
    text = (text or "").strip()
    if not text:
        return None
    for fmt in (DATE_FMT, "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def _today_str():
    return date.today().strftime(DATE_FMT)


def _compute_status(next_due_text):
    """Return (status_label, tag_name) based on the next due date string."""
    if not next_due_text or str(next_due_text).strip() in ("", "None"):
        return "Completed", "completed"
    due = _parse_date(str(next_due_text))
    if due is None:
        return "Completed", "completed"
    today = date.today()
    delta = (due - today).days
    if delta < 0:
        return "Overdue", "overdue"
    if delta <= 30:
        return "Due Soon", "due_soon"
    return "Up to Date", "up_to_date"


def _make_btn(parent, text, command, bg=CORAL, fg=WHITE, padx=16, pady=6, font_size=10):
    btn = tk.Button(
        parent, text=text, command=command,
        bg=bg, fg=fg, activebackground=bg, activeforeground=fg,
        font=(FONT, font_size, "bold"), relief="flat",
        cursor="hand2", padx=padx, pady=pady, bd=0
    )
    btn.bind("<Enter>", lambda e: btn.config(bg=_darken(bg)))
    btn.bind("<Leave>", lambda e: btn.config(bg=bg))
    return btn


def _darken(hex_color, factor=0.88):
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = (int(c * factor) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _style_treeview(tree):
    style = ttk.Style()
    style.theme_use("default")
    tid = str(id(tree))
    style.configure(
        f"Vacc{tid}.Treeview",
        background=TABLE_ROW_ODD,
        fieldbackground=TABLE_ROW_ODD,
        foreground=DARK_TEXT,
        rowheight=30,
        font=(FONT, 10),
    )
    style.configure(
        f"Vacc{tid}.Treeview.Heading",
        background=TABLE_HEADER_BG,
        foreground=TABLE_HEADER_FG,
        font=(FONT, 10, "bold"),
        relief="flat",
    )
    style.map(f"Vacc{tid}.Treeview", background=[("selected", LAVENDER)])
    tree.configure(style=f"Vacc{tid}.Treeview")


# ══════════════════════════════════════════════════════════════════════════════
class VaccinationsModule(tk.Frame):
    """Vaccination management module."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", BG_COLOR)
        super().__init__(parent, **kwargs)

        self._upcoming_visible = False
        self._selected_pet_id  = None   # None = all pets
        self._all_vaccinations = []     # cache for filtering

        self._build_ui()
        self.refresh()

    # ── UI build ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Header
        header = tk.Frame(self, bg=BG_COLOR, pady=10)
        header.pack(fill="x", padx=20)

        tk.Label(header, text="💉  Vaccination Management",
                 font=(FONT, 20, "bold"), bg=BG_COLOR, fg=DARK_TEXT).pack(side="left")
        tk.Label(header, text="Track and manage pet vaccination records",
                 font=(FONT, 10), bg=BG_COLOR, fg="gray").pack(side="left", padx=(12, 0), pady=(6, 0))

        tk.Frame(self, bg=BORDER_COLOR, height=2).pack(fill="x", padx=20)

        # Toolbar
        self._build_toolbar()

        # Upcoming panel (initially hidden)
        self._upcoming_frame = self._build_upcoming_panel()

        # Main treeview
        self._build_treeview()

        # Bottom action bar
        self._build_action_bar()

    # ── Toolbar ────────────────────────────────────────────────────────────────
    def _build_toolbar(self):
        toolbar = tk.Frame(self, bg=BG_COLOR, pady=8)
        toolbar.pack(fill="x", padx=20)

        # Pet filter
        tk.Label(toolbar, text="Filter by Pet:", font=(FONT, 10),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left", padx=(0, 6))

        self._pet_filter_var = tk.StringVar(value="All Pets")
        self._pet_filter_dd  = ttk.Combobox(
            toolbar, textvariable=self._pet_filter_var,
            state="readonly", width=24, font=(FONT, 10)
        )
        self._pet_filter_dd.pack(side="left", padx=(0, 16))
        self._pet_filter_dd.bind("<<ComboboxSelected>>", self._on_pet_filter_change)

        # Upcoming toggle
        self._upcoming_btn = _make_btn(
            toolbar, "🔔  View Upcoming",
            self._toggle_upcoming,
            bg=YELLOW, fg=DARK_TEXT
        )
        self._upcoming_btn.pack(side="left", padx=(0, 8))

        # Alert badge (shown next to button)
        self._badge_var = tk.StringVar(value="")
        self._badge_lbl = tk.Label(
            toolbar, textvariable=self._badge_var,
            font=(FONT, 9, "bold"),
            bg=ERROR_COLOR, fg=WHITE,
            padx=6, pady=2, relief="flat"
        )

        # Add Vaccination
        _make_btn(toolbar, "+ Add Vaccination",
                  self._open_add_dialog, bg=MINT, fg=DARK_TEXT).pack(side="right")

    # ── Upcoming panel ─────────────────────────────────────────────────────────
    def _build_upcoming_panel(self):
        frame = tk.Frame(self, bg=YELLOW, relief="solid", bd=1)
        # Not packed yet — shown on demand

        # Title row
        title_row = tk.Frame(frame, bg=YELLOW)
        title_row.pack(fill="x", padx=12, pady=(8, 4))
        tk.Label(title_row, text="🗓  Vaccinations Due in the Next 30 Days",
                 font=(FONT, 11, "bold"), bg=YELLOW, fg=DARK_TEXT).pack(side="left")
        _make_btn(title_row, "✕ Close",
                  self._toggle_upcoming, bg=CORAL, pady=2, padx=10).pack(side="right")

        # Upcoming treeview
        up_tree_frame = tk.Frame(frame, bg=YELLOW)
        up_tree_frame.pack(fill="x", padx=12, pady=(0, 10))

        cols = ("pet_name", "vaccine", "date_given", "next_due", "days_left")
        self._upcoming_tree = ttk.Treeview(up_tree_frame, columns=cols,
                                           show="headings", height=6,
                                           selectmode="browse")
        for col, label, width in [
            ("pet_name",  "Pet Name",   140),
            ("vaccine",   "Vaccine",    160),
            ("date_given","Date Given", 120),
            ("next_due",  "Next Due",   120),
            ("days_left", "Days Left",   90),
        ]:
            self._upcoming_tree.heading(col, text=label)
            self._upcoming_tree.column(col, width=width, anchor="center")

        _style_treeview(self._upcoming_tree)
        self._upcoming_tree.tag_configure("overdue",  background="#FDDEDE", foreground="#B71C1C")
        self._upcoming_tree.tag_configure("due_soon", background=YELLOW,    foreground="#7B4F00")

        vsb = ttk.Scrollbar(up_tree_frame, orient="vertical",
                             command=self._upcoming_tree.yview)
        self._upcoming_tree.configure(yscrollcommand=vsb.set)
        self._upcoming_tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")

        return frame

    # ── Main treeview ──────────────────────────────────────────────────────────
    def _build_treeview(self):
        tree_container = tk.Frame(self, bg=BG_COLOR)
        tree_container.pack(fill="both", expand=True, padx=20, pady=6)

        cols = ("vacc_id", "pet_name", "species",
                "vaccine_name", "date_given", "next_due", "status")
        self._tree = ttk.Treeview(tree_container, columns=cols,
                                  show="headings", selectmode="browse")

        for col, label, width in [
            ("vacc_id",      "Vacc ID",      70),
            ("pet_name",     "Pet Name",    140),
            ("species",      "Species",     110),
            ("vaccine_name", "Vaccine",     150),
            ("date_given",   "Date Given",  120),
            ("next_due",     "Next Due",    120),
            ("status",       "Status",      110),
        ]:
            self._tree.heading(col, text=label,
                               command=lambda c=col: self._sort_tree(c, False))
            self._tree.column(col, width=width, anchor="center")

        _style_treeview(self._tree)

        # Status colour tags
        self._tree.tag_configure("overdue",    background="#FDDEDE", foreground="#B71C1C")
        self._tree.tag_configure("due_soon",   background=YELLOW,    foreground="#7B4F00")
        self._tree.tag_configure("up_to_date", background="#C8F0D8", foreground="#1B5E20")
        self._tree.tag_configure("completed",  background="#E8E8E8", foreground="#555555")
        self._tree.tag_configure("odd",        background=TABLE_ROW_ODD)
        self._tree.tag_configure("even",       background=TABLE_ROW_EVEN)

        vsb = ttk.Scrollbar(tree_container, orient="vertical",
                             command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_container, orient="horizontal",
                             command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_container.rowconfigure(0, weight=1)
        tree_container.columnconfigure(0, weight=1)

    # ── Action bar ─────────────────────────────────────────────────────────────
    def _build_action_bar(self):
        bar = tk.Frame(self, bg=BG_COLOR, pady=6)
        bar.pack(fill="x", padx=20)

        _make_btn(bar, "✏  Edit",
                  self._edit_vaccination, bg=LAVENDER, fg=DARK_TEXT).pack(side="left", padx=(0, 8))
        _make_btn(bar, "🗑  Delete",
                  self.delete_vaccination, bg=ERROR_COLOR).pack(side="left")

    # ── Upcoming panel toggle ──────────────────────────────────────────────────
    def _toggle_upcoming(self):
        if self._upcoming_visible:
            self._upcoming_frame.pack_forget()
            self._upcoming_visible = False
            self._upcoming_btn.config(text="🔔  View Upcoming")
        else:
            self._upcoming_frame.pack(fill="x", padx=20, pady=(0, 6))
            self._upcoming_visible = True
            self._upcoming_btn.config(text="🔔  Hide Upcoming")
            self.show_upcoming()

    # ── Load data ──────────────────────────────────────────────────────────────
    def load_vaccinations(self):
        """Fetch all vaccination records from DB and populate the treeview."""
        try:
            self._all_vaccinations = db.get_all_vaccinations()
        except Exception:
            self._all_vaccinations = []

        # Refresh pet filter dropdown
        pet_names = sorted({
            f"{v.get('pet_id')} - {v.get('pet_name', '')}"
            for v in self._all_vaccinations
            if v.get("pet_name")
        })
        self._pet_filter_dd.configure(values=["All Pets"] + pet_names)
        if self._pet_filter_var.get() not in ["All Pets"] + pet_names:
            self._pet_filter_var.set("All Pets")
            self._selected_pet_id = None

        self._populate_main_tree(self._all_vaccinations)
        self._refresh_badge()

    def _populate_main_tree(self, vaccinations):
        for item in self._tree.get_children():
            self._tree.delete(item)

        odd = True
        for v in vaccinations:
            status, tag = _compute_status(v.get("next_due_date"))
            # Only use status tag for colour; odd/even as fallback for completed
            row_tag = tag
            self._tree.insert("", "end", values=(
                v.get("id", ""),
                v.get("pet_name", ""),
                v.get("species", ""),
                v.get("vaccine_name", ""),
                v.get("date_given", ""),
                v.get("next_due_date", ""),
                status,
            ), tags=(row_tag,))
            odd = not odd

    def _refresh_badge(self):
        """Count overdue / due-soon records and update the alert badge."""
        count = 0
        today = date.today()
        for v in self._all_vaccinations:
            due = _parse_date(str(v.get("next_due_date", "")))
            if due is not None and (due - today).days <= 30:
                count += 1
        if count > 0:
            self._badge_var.set(f"  {count} alert{'s' if count > 1 else ''}  ")
            self._badge_lbl.pack(side="left", padx=(0, 8))
        else:
            self._badge_var.set("")
            self._badge_lbl.pack_forget()

    # ── Filtering ──────────────────────────────────────────────────────────────
    def _on_pet_filter_change(self, event=None):
        val = self._pet_filter_var.get()
        if val == "All Pets":
            self._selected_pet_id = None
            self._populate_main_tree(self._all_vaccinations)
        else:
            pet_id_str = val.split(" - ")[0]
            try:
                self._selected_pet_id = int(pet_id_str)
            except ValueError:
                self._selected_pet_id = None
            self.filter_by_pet(self._selected_pet_id)

    def filter_by_pet(self, pet_id):
        """Display only vaccinations for the given pet_id."""
        filtered = [v for v in self._all_vaccinations
                    if v.get("pet_id") == pet_id]
        self._populate_main_tree(filtered)

    def show_upcoming(self):
        """Populate the upcoming vaccinations panel."""
        for item in self._upcoming_tree.get_children():
            self._upcoming_tree.delete(item)

        today = date.today()
        upcoming = []
        for v in self._all_vaccinations:
            due = _parse_date(str(v.get("next_due_date", "")))
            if due is not None:
                delta = (due - today).days
                if delta <= 30:
                    upcoming.append((delta, v))

        upcoming.sort(key=lambda x: x[0])

        for delta, v in upcoming:
            _, tag = _compute_status(v.get("next_due_date"))
            days_text = f"{delta} days" if delta >= 0 else f"Overdue {abs(delta)}d"
            self._upcoming_tree.insert("", "end", values=(
                v.get("pet_name", ""),
                v.get("vaccine_name", ""),
                v.get("date_given", ""),
                v.get("next_due_date", ""),
                days_text,
            ), tags=(tag,))

    # ── CRUD actions ───────────────────────────────────────────────────────────
    def _get_selected_vacc(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select a vaccination record first.")
            return None
        return self._tree.item(sel[0], "values")

    def _open_add_dialog(self):
        try:
            pets = db.get_all_pets()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load pets:\n{exc}")
            return
        _VaccinationDialog(self, pets=pets, on_save=self.refresh)

    def _edit_vaccination(self):
        row = self._get_selected_vacc()
        if row is None:
            return
        vacc_id = int(row[0])
        try:
            vacc = db.get_vaccination(vacc_id)
            pets = db.get_all_pets()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load record:\n{exc}")
            return
        _VaccinationDialog(self, pets=pets, vaccination=vacc, on_save=self.refresh)

    def delete_vaccination(self):
        row = self._get_selected_vacc()
        if row is None:
            return
        vacc_id  = int(row[0])
        pet_name = row[1]
        vaccine  = row[3]
        if messagebox.askyesno(
            "Confirm Delete",
            f"Delete '{vaccine}' vaccination record for {pet_name}?\n"
            "This cannot be undone."
        ):
            try:
                db.delete_vaccination(vacc_id)
                messagebox.showinfo("Deleted", "Vaccination record deleted.")
                self.refresh()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not delete:\n{exc}")

    # ── Refresh ────────────────────────────────────────────────────────────────
    def refresh(self):
        self.load_vaccinations()
        if self._upcoming_visible:
            self.show_upcoming()

    def _sort_tree(self, col, reverse):
        data = [(self._tree.set(k, col), k)
                for k in self._tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self._tree.move(k, "", idx)
        self._tree.heading(col,
                           command=lambda: self._sort_tree(col, not reverse))


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Add / Edit Vaccination
# ══════════════════════════════════════════════════════════════════════════════
class _VaccinationDialog(tk.Toplevel):
    def __init__(self, parent, pets, vaccination=None, on_save=None):
        super().__init__(parent)
        self._pets       = pets         # list of dicts with id, name
        self._vaccination = vaccination  # None → add mode
        self.on_save     = on_save

        title = "Edit Vaccination" if vaccination else "Add Vaccination"
        self.title(title)
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if vaccination:
            self._populate(vaccination)
        self._center()

    def _center(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        x = (self.winfo_screenwidth()  - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        title_text = "Edit Vaccination" if self._vaccination else "Add Vaccination Record"
        tk.Label(self, text=title_text,
                 font=(FONT, 15, "bold"), bg=BG_COLOR, fg=DARK_TEXT).pack(padx=20, pady=(16, 2))
        tk.Frame(self, bg=BORDER_COLOR, height=1).pack(fill="x", padx=20, pady=4)

        form = tk.Frame(self, bg=BG_COLOR)
        form.pack(fill="x", padx=20, pady=6)

        # Pet dropdown
        tk.Label(form, text="Pet *", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=0, column=0, sticky="w", pady=4)
        self._pet_var = tk.StringVar()
        pet_labels = [f"{p.get('id')} - {p.get('name', '')}"
                      for p in self._pets]
        self._pet_dd = ttk.Combobox(form, textvariable=self._pet_var,
                                    values=pet_labels, state="readonly",
                                    width=34, font=(FONT, 10))
        self._pet_dd.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        # Vaccine Name (combobox with suggestions, editable)
        tk.Label(form, text="Vaccine Name *", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=1, column=0, sticky="w", pady=4)
        self._vaccine_var = tk.StringVar()
        self._vaccine_dd  = ttk.Combobox(
            form, textvariable=self._vaccine_var,
            values=COMMON_VACCINES, width=34, font=(FONT, 10)
        )
        self._vaccine_dd.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        # Date Given
        tk.Label(form, text="Date Given *", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=2, column=0, sticky="w", pady=4)

        date_frame = tk.Frame(form, bg=BG_COLOR)
        date_frame.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)
        self._date_given_var = tk.StringVar()
        tk.Entry(date_frame, textvariable=self._date_given_var,
                 font=(FONT, 10), bg=WHITE, fg=DARK_TEXT,
                 relief="solid", bd=1, width=22).pack(side="left")
        tk.Label(date_frame, text=" (DD-MM-YYYY)",
                 font=(FONT, 9), bg=BG_COLOR, fg="gray").pack(side="left")
        _make_btn(date_frame, "Today", self._fill_today_given,
                  bg=MINT, fg=DARK_TEXT, padx=8, pady=2).pack(side="left", padx=(6, 0))

        # Next Due Date
        tk.Label(form, text="Next Due Date", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=3, column=0, sticky="w", pady=4)

        due_frame = tk.Frame(form, bg=BG_COLOR)
        due_frame.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)
        self._next_due_var = tk.StringVar()
        tk.Entry(due_frame, textvariable=self._next_due_var,
                 font=(FONT, 10), bg=WHITE, fg=DARK_TEXT,
                 relief="solid", bd=1, width=22).pack(side="left")
        tk.Label(due_frame, text=" (DD-MM-YYYY, optional)",
                 font=(FONT, 9), bg=BG_COLOR, fg="gray").pack(side="left")

        # Notes
        tk.Label(form, text="Notes", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=4, column=0, sticky="nw", pady=4)
        self._notes = tk.Text(form, width=35, height=3, font=(FONT, 10),
                              bg=WHITE, fg=DARK_TEXT, relief="solid", bd=1)
        self._notes.grid(row=4, column=1, sticky="ew", padx=(10, 0), pady=4)

        form.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(pady=(4, 16))
        _make_btn(btn_frame, "Save", self._save, bg=MINT, fg=DARK_TEXT).pack(side="left", padx=8)
        _make_btn(btn_frame, "Cancel", self.destroy, bg=CORAL).pack(side="left", padx=8)

    def _fill_today_given(self):
        self._date_given_var.set(_today_str())

    def _populate(self, v):
        # Set pet dropdown
        pid = v.get("pet_id")
        pname = v.get("pet_name", "")
        for label in self._pet_dd["values"]:
            if label.startswith(str(pid) + " - "):
                self._pet_var.set(label)
                break
        self._vaccine_var.set(v.get("vaccine_name", ""))
        self._date_given_var.set(v.get("date_given", ""))
        self._next_due_var.set(v.get("next_due_date", ""))
        self._notes.insert("1.0", v.get("notes", ""))

    def _validate_date_field(self, text, label):
        """Return parsed date or raise messagebox and return False on error."""
        if not text.strip():
            return None
        d = _parse_date(text)
        if d is None:
            messagebox.showwarning(
                "Validation",
                f"'{label}' must be in DD-MM-YYYY format.",
                parent=self
            )
            return False
        return d

    def _save(self):
        pet_val      = self._pet_var.get().strip()
        vaccine_name = self._vaccine_var.get().strip()
        date_given   = self._date_given_var.get().strip()
        next_due     = self._next_due_var.get().strip()
        notes        = self._notes.get("1.0", "end").strip()

        # Validation
        if not pet_val:
            messagebox.showwarning("Validation", "Please select a pet.", parent=self)
            return
        if not vaccine_name:
            messagebox.showwarning("Validation", "Vaccine name is required.", parent=self)
            return
        if not date_given:
            messagebox.showwarning("Validation", "Date Given is required.", parent=self)
            return

        parsed_given = self._validate_date_field(date_given, "Date Given")
        if parsed_given is False:
            return
        if next_due:
            parsed_due = self._validate_date_field(next_due, "Next Due Date")
            if parsed_due is False:
                return
        else:
            parsed_due = None

        pet_id = int(pet_val.split(" - ")[0])

        try:
            if self._vaccination:
                db.update_vaccination(
                    vacc_id=self._vaccination["id"],
                    pet_id=pet_id,
                    vaccine_name=vaccine_name,
                    date_given=date_given,
                    next_due_date=next_due if next_due else None,
                    notes=notes,
                )
                messagebox.showinfo("Updated",
                                    "Vaccination record updated!", parent=self)
            else:
                db.add_vaccination(
                    pet_id=pet_id,
                    vaccine_name=vaccine_name,
                    date_given=date_given,
                    next_due_date=next_due if next_due else None,
                    notes=notes,
                )
                messagebox.showinfo("Added",
                                    "Vaccination record added!", parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()

        except Exception as exc:
            messagebox.showerror("Error", f"Could not save:\n{exc}", parent=self)
