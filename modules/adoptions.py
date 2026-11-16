"""
adoptions.py — Adoptions Module for PawPal
Handles Adoption Applications and Adopter Registry tabs.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
import re

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


# ── Helper: styled button ───────────────────────────────────────────────────────
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
    """Return a slightly darker shade of *hex_color*."""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    r, g, b = (int(c * factor) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _style_treeview(tree, columns):
    """Apply consistent styling to a ttk.Treeview widget."""
    style = ttk.Style()
    style.theme_use("default")
    tid = str(id(tree))
    style.configure(
        f"Custom{tid}.Treeview",
        background=TABLE_ROW_ODD,
        fieldbackground=TABLE_ROW_ODD,
        foreground=DARK_TEXT,
        rowheight=30,
        font=(FONT, 10),
    )
    style.configure(
        f"Custom{tid}.Treeview.Heading",
        background=TABLE_HEADER_BG,
        foreground=TABLE_HEADER_FG,
        font=(FONT, 10, "bold"),
        relief="flat",
    )
    style.map(f"Custom{tid}.Treeview", background=[("selected", LAVENDER)])
    tree.configure(style=f"Custom{tid}.Treeview")


# ══════════════════════════════════════════════════════════════════════════════
class AdoptionsModule(tk.Frame):
    """Main adoptions module with two custom sub-tabs."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", BG_COLOR)
        super().__init__(parent, **kwargs)

        self._active_tab = tk.StringVar(value="applications")
        self._build_ui()
        self.refresh()

    # ── UI skeleton ────────────────────────────────────────────────────────────
    def _build_ui(self):
        # Page header
        header = tk.Frame(self, bg=BG_COLOR, pady=10)
        header.pack(fill="x", padx=20)
        tk.Label(header, text="🐾  Adoptions", font=(FONT, 20, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left")

        # Custom tab bar
        tab_bar = tk.Frame(self, bg=BG_COLOR)
        tab_bar.pack(fill="x", padx=20, pady=(0, 4))

        self._tab_btns = {}
        for key, label in [("applications", "Adoption Applications"),
                            ("adopters",     "Adopter Registry")]:
            btn = tk.Button(
                tab_bar, text=label,
                font=(FONT, 11, "bold"), relief="flat", cursor="hand2",
                padx=20, pady=8, bd=0,
                command=lambda k=key: self._switch_tab(k),
            )
            btn.pack(side="left", padx=(0, 4))
            self._tab_btns[key] = btn

        # Separator
        tk.Frame(self, bg=BORDER_COLOR, height=2).pack(fill="x", padx=20)

        # Content area
        self._content = tk.Frame(self, bg=BG_COLOR)
        self._content.pack(fill="both", expand=True, padx=20, pady=10)

        # Build both tab contents (hidden until selected)
        self._frame_applications = self._build_applications_tab(self._content)
        self._frame_adopters     = self._build_adopters_tab(self._content)

        self._switch_tab("applications")

    def _switch_tab(self, key):
        self._active_tab.set(key)
        # Style active / inactive tabs
        for k, btn in self._tab_btns.items():
            if k == key:
                btn.config(bg=DARK_TEXT, fg=WHITE)
            else:
                btn.config(bg=BORDER_COLOR, fg=DARK_TEXT)
        # Show / hide frames
        for k, frame in [("applications", self._frame_applications),
                          ("adopters",     self._frame_adopters)]:
            if k == key:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — Adoption Applications
    # ══════════════════════════════════════════════════════════════════════════
    def _build_applications_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)

        # ── Top toolbar ────────────────────────────────────────────────────────
        toolbar = tk.Frame(frame, bg=BG_COLOR, pady=6)
        toolbar.pack(fill="x")

        tk.Label(toolbar, text="Filter by Status:", font=(FONT, 10),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left", padx=(0, 6))

        self._app_status_var = tk.StringVar(value="All")
        status_dd = ttk.Combobox(
            toolbar, textvariable=self._app_status_var,
            values=["All", "Pending", "Approved", "Rejected"],
            state="readonly", width=14, font=(FONT, 10)
        )
        status_dd.pack(side="left", padx=(0, 12))
        status_dd.bind("<<ComboboxSelected>>", lambda e: self.filter_applications())

        _make_btn(toolbar, "+ New Application",
                  self._open_new_application_dialog,
                  bg=MINT, fg=DARK_TEXT).pack(side="right")

        # ── Treeview ───────────────────────────────────────────────────────────
        tree_frame = tk.Frame(frame, bg=BG_COLOR)
        tree_frame.pack(fill="both", expand=True, pady=6)

        cols = ("app_id", "pet_name", "adopter_name", "date", "status")
        self._app_tree = ttk.Treeview(tree_frame, columns=cols,
                                      show="headings", selectmode="browse")
        headings = {
            "app_id":       ("App ID",       60),
            "pet_name":     ("Pet Name",     160),
            "adopter_name": ("Adopter Name", 180),
            "date":         ("Date",         120),
            "status":       ("Status",       110),
        }
        for col, (label, width) in headings.items():
            self._app_tree.heading(col, text=label,
                                   command=lambda c=col: self._sort_app_tree(c, False))
            self._app_tree.column(col, width=width, anchor="center")

        _style_treeview(self._app_tree, cols)

        # Status colour tags
        self._app_tree.tag_configure("Pending",  background=YELLOW,       foreground=DARK_TEXT)
        self._app_tree.tag_configure("Approved", background="#C8F0D8",    foreground="#1B5E20")
        self._app_tree.tag_configure("Rejected", background="#FDDEDE",    foreground="#B71C1C")
        self._app_tree.tag_configure("odd",  background=TABLE_ROW_ODD)
        self._app_tree.tag_configure("even", background=TABLE_ROW_EVEN)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._app_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self._app_tree.xview)
        self._app_tree.configure(yscrollcommand=vsb.set,
                                  xscrollcommand=hsb.set)

        self._app_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # ── Action bar ─────────────────────────────────────────────────────────
        action_bar = tk.Frame(frame, bg=BG_COLOR, pady=6)
        action_bar.pack(fill="x")

        _make_btn(action_bar, "✔  Approve",
                  self._approve_application, bg=SUCCESS_COLOR).pack(side="left", padx=(0, 8))
        _make_btn(action_bar, "✖  Reject",
                  self._reject_application, bg=ERROR_COLOR).pack(side="left", padx=(0, 8))
        _make_btn(action_bar, "🔍  View Details",
                  self._view_application_details, bg=LAVENDER, fg=DARK_TEXT).pack(side="left")

        return frame

    # ── Application actions ────────────────────────────────────────────────────
    def _get_selected_app(self):
        sel = self._app_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select an application first.")
            return None
        return self._app_tree.item(sel[0], "values")

    def _approve_application(self):
        row = self._get_selected_app()
        if row is None:
            return
        app_id, pet_name, _, _, status = row
        if status == "Approved":
            messagebox.showinfo("Already Approved",
                                "This application is already approved.")
            return
        # Guard: pet already adopted?
        try:
            pet_status = db.get_pet_adoption_status(pet_name)
        except Exception:
            pet_status = None
        if pet_status == "Adopted":
            messagebox.showerror(
                "Cannot Approve",
                f"'{pet_name}' has already been adopted. "
                "Please reject this application."
            )
            return
        if messagebox.askyesno("Confirm Approval",
                               f"Approve application #{app_id} for {pet_name}?"):
            try:
                db.approve_application(int(app_id))
                messagebox.showinfo("Success",
                                    "Application approved successfully!")
                self.load_applications()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not approve:\n{exc}")

    def _reject_application(self):
        row = self._get_selected_app()
        if row is None:
            return
        app_id, pet_name, _, _, status = row
        if status == "Rejected":
            messagebox.showinfo("Already Rejected",
                                "This application is already rejected.")
            return
        if messagebox.askyesno("Confirm Rejection",
                               f"Reject application #{app_id} for {pet_name}?"):
            try:
                db.reject_application(int(app_id))
                messagebox.showinfo("Success",
                                    "Application rejected.")
                self.load_applications()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not reject:\n{exc}")

    def _view_application_details(self):
        row = self._get_selected_app()
        if row is None:
            return
        app_id = int(row[0])
        try:
            app  = db.get_application(app_id)
            pet  = db.get_pet(app.get("pet_id"))
            adp  = db.get_adopter(app.get("adopter_id"))
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load details:\n{exc}")
            return
        _ApplicationDetailsDialog(self, app, pet, adp)

    # ── New Application Dialog ─────────────────────────────────────────────────
    def _open_new_application_dialog(self):
        try:
            pets     = db.get_available_pets()
            adopters = db.get_all_adopters()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load data:\n{exc}")
            return
        _NewApplicationDialog(self, pets, adopters,
                              on_save=self.load_applications)

    # ── Load / filter ──────────────────────────────────────────────────────────
    def load_applications(self):
        for item in self._app_tree.get_children():
            self._app_tree.delete(item)
        try:
            apps = db.get_all_applications()
        except Exception:
            apps = []
        status_filter = self._app_status_var.get()
        odd = True
        for app in apps:
            status = app.get("status", "Pending")
            if status_filter != "All" and status != status_filter:
                continue
            tag = status if status in ("Pending", "Approved", "Rejected") else ("odd" if odd else "even")
            values = (
                app.get("id", ""),
                app.get("pet_name", ""),
                app.get("adopter_name", ""),
                app.get("application_date", ""),
                status,
            )
            self._app_tree.insert("", "end", values=values, tags=(tag,))
            odd = not odd

    def filter_applications(self):
        self.load_applications()

    def _sort_app_tree(self, col, reverse):
        data = [(self._app_tree.set(k, col), k)
                for k in self._app_tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self._app_tree.move(k, "", idx)
        self._app_tree.heading(
            col, command=lambda: self._sort_app_tree(col, not reverse))

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — Adopter Registry
    # ══════════════════════════════════════════════════════════════════════════
    def _build_adopters_tab(self, parent):
        frame = tk.Frame(parent, bg=BG_COLOR)

        # ── Search bar ─────────────────────────────────────────────────────────
        search_bar = tk.Frame(frame, bg=BG_COLOR, pady=6)
        search_bar.pack(fill="x")

        tk.Label(search_bar, text="🔍", font=(FONT, 12),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left", padx=(0, 4))

        self._adopter_search_var = tk.StringVar()
        search_entry = tk.Entry(
            search_bar, textvariable=self._adopter_search_var,
            font=(FONT, 11), bg=WHITE, fg=DARK_TEXT,
            relief="solid", bd=1, width=30
        )
        search_entry.pack(side="left", padx=(0, 8))
        search_entry.insert(0, "Search by name or email…")
        search_entry.config(fg="gray")
        search_entry.bind("<FocusIn>",  lambda e: self._clear_placeholder(search_entry))
        search_entry.bind("<FocusOut>", lambda e: self._restore_placeholder(search_entry))
        search_entry.bind("<KeyRelease>", lambda e: self.search_adopters())

        _make_btn(search_bar, "+ Add Adopter",
                  self._open_add_adopter_dialog, bg=MINT, fg=DARK_TEXT).pack(side="right")

        # ── Treeview ───────────────────────────────────────────────────────────
        tree_frame = tk.Frame(frame, bg=BG_COLOR)
        tree_frame.pack(fill="both", expand=True, pady=6)

        cols = ("id", "full_name", "phone", "email", "date_registered")
        self._adopter_tree = ttk.Treeview(tree_frame, columns=cols,
                                          show="headings", selectmode="browse")
        headings = {
            "id":              ("ID",              60),
            "full_name":       ("Full Name",       180),
            "phone":           ("Phone",           130),
            "email":           ("Email",           200),
            "date_registered": ("Date Registered", 130),
        }
        for col, (label, width) in headings.items():
            self._adopter_tree.heading(col, text=label,
                                       command=lambda c=col: self._sort_adopter_tree(c, False))
            self._adopter_tree.column(col, width=width, anchor="center")

        _style_treeview(self._adopter_tree, cols)
        self._adopter_tree.tag_configure("odd",  background=TABLE_ROW_ODD)
        self._adopter_tree.tag_configure("even", background=TABLE_ROW_EVEN)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                             command=self._adopter_tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",
                             command=self._adopter_tree.xview)
        self._adopter_tree.configure(yscrollcommand=vsb.set,
                                      xscrollcommand=hsb.set)

        self._adopter_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # ── Bottom action bar ──────────────────────────────────────────────────
        action_bar = tk.Frame(frame, bg=BG_COLOR, pady=6)
        action_bar.pack(fill="x")

        _make_btn(action_bar, "✏  Edit",
                  self._edit_adopter, bg=LAVENDER, fg=DARK_TEXT).pack(side="left", padx=(0, 8))
        _make_btn(action_bar, "🗑  Delete",
                  self._delete_adopter, bg=ERROR_COLOR).pack(side="left")

        return frame

    # ── Placeholder helpers ────────────────────────────────────────────────────
    def _clear_placeholder(self, entry):
        if entry.get() == "Search by name or email…":
            entry.delete(0, "end")
            entry.config(fg=DARK_TEXT)

    def _restore_placeholder(self, entry):
        if entry.get() == "":
            entry.insert(0, "Search by name or email…")
            entry.config(fg="gray")

    # ── Adopter actions ────────────────────────────────────────────────────────
    def _get_selected_adopter(self):
        sel = self._adopter_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection",
                                   "Please select an adopter first.")
            return None
        return self._adopter_tree.item(sel[0], "values")

    def _open_add_adopter_dialog(self):
        _AdopterDialog(self, on_save=self.load_adopters)

    def _edit_adopter(self):
        row = self._get_selected_adopter()
        if row is None:
            return
        adopter_id = int(row[0])
        try:
            adopter = db.get_adopter(adopter_id)
        except Exception as exc:
            messagebox.showerror("Error", f"Could not load adopter:\n{exc}")
            return
        _AdopterDialog(self, adopter=adopter, on_save=self.load_adopters)

    def _delete_adopter(self):
        row = self._get_selected_adopter()
        if row is None:
            return
        adopter_id, name = int(row[0]), row[1]
        if messagebox.askyesno("Confirm Delete",
                               f"Delete adopter '{name}'?\nThis cannot be undone."):
            try:
                db.delete_adopter(adopter_id)
                messagebox.showinfo("Deleted", f"'{name}' has been removed.")
                self.load_adopters()
            except Exception as exc:
                messagebox.showerror("Error", f"Could not delete:\n{exc}")

    # ── Load / search ──────────────────────────────────────────────────────────
    def load_adopters(self, query=""):
        for item in self._adopter_tree.get_children():
            self._adopter_tree.delete(item)
        try:
            adopters = db.get_all_adopters()
        except Exception:
            adopters = []
        q = query.lower().strip()
        odd = True
        for a in adopters:
            name  = a.get("full_name", "")
            email = a.get("email", "")
            if q and q not in name.lower() and q not in email.lower():
                continue
            tag = "odd" if odd else "even"
            self._adopter_tree.insert("", "end", values=(
                a.get("id", ""),
                name,
                a.get("phone", ""),
                email,
                a.get("date_registered", ""),
            ), tags=(tag,))
            odd = not odd

    def search_adopters(self):
        query = self._adopter_search_var.get()
        if query == "Search by name or email…":
            query = ""
        self.load_adopters(query)

    def _sort_adopter_tree(self, col, reverse):
        data = [(self._adopter_tree.set(k, col), k)
                for k in self._adopter_tree.get_children("")]
        data.sort(reverse=reverse)
        for idx, (_, k) in enumerate(data):
            self._adopter_tree.move(k, "", idx)
        self._adopter_tree.heading(
            col, command=lambda: self._sort_adopter_tree(col, not reverse))

    # ── Global refresh ─────────────────────────────────────────────────────────
    def refresh(self):
        self.load_applications()
        self.load_adopters()


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: New Application
# ══════════════════════════════════════════════════════════════════════════════
class _NewApplicationDialog(tk.Toplevel):
    def __init__(self, parent, pets, adopters, on_save=None):
        super().__init__(parent)
        self.on_save = on_save
        self._pets    = pets    # list of dicts with id, name
        self._adopters = adopters  # list of dicts with id, full_name

        self.title("New Adoption Application")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), self.winfo_width(), 440)
        h = max(self.winfo_reqheight(), self.winfo_height(), 320)
        x = max(0, (self.winfo_screenwidth()  - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        pad = {"padx": 20, "pady": 6}

        tk.Label(self, text="New Adoption Application",
                 font=(FONT, 15, "bold"), bg=BG_COLOR, fg=DARK_TEXT).pack(padx=20, pady=(16, 2))
        tk.Frame(self, bg=BORDER_COLOR, height=1).pack(fill="x", padx=20, pady=4)

        form = tk.Frame(self, bg=BG_COLOR)
        form.pack(fill="x", padx=20, pady=6)

        # Pet dropdown
        tk.Label(form, text="Select Pet *", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=0, column=0, sticky="w", pady=4)
        self._pet_var = tk.StringVar()
        pet_labels = [f"{p.get('id')} - {p.get('name', '')}" for p in self._pets]
        self._pet_dd = ttk.Combobox(form, textvariable=self._pet_var,
                                    values=pet_labels, state="readonly",
                                    width=35, font=(FONT, 10))
        self._pet_dd.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=4)

        # Adopter dropdown
        tk.Label(form, text="Select Adopter *", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=1, column=0, sticky="w", pady=4)
        self._adopter_var = tk.StringVar()
        adopter_labels = [f"{a.get('id')} - {a.get('full_name', '')}"
                          for a in self._adopters]
        self._adopter_dd = ttk.Combobox(form, textvariable=self._adopter_var,
                                        values=adopter_labels, state="readonly",
                                        width=35, font=(FONT, 10))
        self._adopter_dd.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=4)

        # Date (auto-filled)
        tk.Label(form, text="Application Date", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=2, column=0, sticky="w", pady=4)
        self._date_var = tk.StringVar(value=date.today().strftime("%d-%m-%Y"))
        tk.Entry(form, textvariable=self._date_var, font=(FONT, 10),
                 bg=WHITE, fg=DARK_TEXT, relief="solid", bd=1,
                 width=37).grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=4)

        # Notes
        tk.Label(form, text="Notes", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=3, column=0, sticky="nw", pady=4)
        self._notes = tk.Text(form, width=37, height=4, font=(FONT, 10),
                              bg=WHITE, fg=DARK_TEXT, relief="solid", bd=1)
        self._notes.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)

        form.columnconfigure(1, weight=1)

        # Buttons
        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(pady=(4, 16))
        _make_btn(btn_frame, "Save", self._save, bg=MINT, fg=DARK_TEXT).pack(side="left", padx=8)
        _make_btn(btn_frame, "Cancel", self.destroy, bg=CORAL).pack(side="left", padx=8)

    def _save(self):
        pet_val     = self._pet_var.get().strip()
        adopter_val = self._adopter_var.get().strip()
        notes       = self._notes.get("1.0", "end").strip()
        app_date    = self._date_var.get().strip()

        if not pet_val:
            messagebox.showwarning("Validation", "Please select a pet.", parent=self)
            return
        if not adopter_val:
            messagebox.showwarning("Validation", "Please select an adopter.", parent=self)
            return

        pet_id     = int(pet_val.split(" - ")[0])
        adopter_id = int(adopter_val.split(" - ")[0])

        try:
            db.add_application(pet_id=pet_id, adopter_id=adopter_id,
                                application_date=app_date, notes=notes)
            messagebox.showinfo("Success", "Application submitted!", parent=self)
            if self.on_save:
                self.on_save()
            self.destroy()
        except Exception as exc:
            messagebox.showerror("Error", f"Could not save:\n{exc}", parent=self)


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Application Details
# ══════════════════════════════════════════════════════════════════════════════
class _ApplicationDetailsDialog(tk.Toplevel):
    def __init__(self, parent, app, pet, adopter):
        super().__init__(parent)
        self._app     = app
        self._pet     = pet
        self._adopter = adopter

        self.title(f"Application #{app.get('id', '')} Details")
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self._center()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), self.winfo_width(), 460)
        h = max(self.winfo_reqheight(), self.winfo_height(), 400)
        x = max(0, (self.winfo_screenwidth()  - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        def row(frame, label, value, r):
            tk.Label(frame, text=label, font=(FONT, 10, "bold"),
                     bg=WHITE, fg=DARK_TEXT, width=20, anchor="w").grid(
                         row=r, column=0, sticky="w", padx=10, pady=4)
            tk.Label(frame, text=str(value), font=(FONT, 10),
                     bg=WHITE, fg=DARK_TEXT, anchor="w").grid(
                         row=r, column=1, sticky="w", padx=10, pady=4)

        tk.Label(self, text=f"Application Details  #{self._app.get('id','')}",
                 font=(FONT, 15, "bold"), bg=BG_COLOR, fg=DARK_TEXT).pack(padx=20, pady=(16, 4))
        tk.Frame(self, bg=BORDER_COLOR, height=1).pack(fill="x", padx=20, pady=2)

        # Application section
        tk.Label(self, text="📋  Application Info", font=(FONT, 11, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(anchor="w", padx=24, pady=(8, 2))
        app_frame = tk.Frame(self, bg=WHITE, relief="solid", bd=1)
        app_frame.pack(fill="x", padx=20, pady=4)
        a = self._app
        for r, (lbl, key) in enumerate([
            ("Application ID",   "id"),
            ("Status",           "status"),
            ("Application Date", "application_date"),
            ("Notes",            "notes"),
        ]):
            row(app_frame, lbl, a.get(key, "—"), r)

        # Pet section
        tk.Label(self, text="🐾  Pet Info", font=(FONT, 11, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(anchor="w", padx=24, pady=(8, 2))
        pet_frame = tk.Frame(self, bg=WHITE, relief="solid", bd=1)
        pet_frame.pack(fill="x", padx=20, pady=4)
        p = self._pet or {}
        for r, (lbl, key) in enumerate([
            ("Name",    "name"),
            ("Species", "species"),
            ("Breed",   "breed"),
        ]):
            row(pet_frame, lbl, p.get(key, "—"), r)

        # Adopter section
        tk.Label(self, text="👤  Adopter Info", font=(FONT, 11, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(anchor="w", padx=24, pady=(8, 2))
        adp_frame = tk.Frame(self, bg=WHITE, relief="solid", bd=1)
        adp_frame.pack(fill="x", padx=20, pady=4)
        d = self._adopter or {}
        for r, (lbl, key) in enumerate([
            ("Full Name", "full_name"),
            ("Phone",     "phone"),
            ("Email",     "email"),
        ]):
            row(adp_frame, lbl, d.get(key, "—"), r)

        _make_btn(self, "Close", self.destroy, bg=CORAL).pack(pady=(8, 16))


# ══════════════════════════════════════════════════════════════════════════════
# Dialog: Add / Edit Adopter
# ══════════════════════════════════════════════════════════════════════════════
class _AdopterDialog(tk.Toplevel):
    def __init__(self, parent, adopter=None, on_save=None):
        super().__init__(parent)
        self._adopter = adopter   # None → add mode
        self.on_save  = on_save

        title = "Edit Adopter" if adopter else "Add Adopter"
        self.title(title)
        self.configure(bg=BG_COLOR)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if adopter:
            self._populate(adopter)
        self._center()

    def _center(self):
        self.update_idletasks()
        w = max(self.winfo_reqwidth(), self.winfo_width(), 460)
        h = max(self.winfo_reqheight(), self.winfo_height(), 400)
        x = max(0, (self.winfo_screenwidth()  - w) // 2)
        y = max(0, (self.winfo_screenheight() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build(self):
        title_text = "Edit Adopter" if self._adopter else "Add Adopter"
        tk.Label(self, text=title_text,
                 font=(FONT, 15, "bold"), bg=BG_COLOR, fg=DARK_TEXT).pack(padx=20, pady=(16, 2))
        tk.Frame(self, bg=BORDER_COLOR, height=1).pack(fill="x", padx=20, pady=4)

        form = tk.Frame(self, bg=BG_COLOR)
        form.pack(fill="x", padx=20, pady=6)

        def lbl_entry(label, row_idx, required=False):
            suffix = " *" if required else ""
            tk.Label(form, text=label + suffix, font=(FONT, 10, "bold"),
                     bg=BG_COLOR, fg=DARK_TEXT).grid(
                         row=row_idx, column=0, sticky="w", pady=4)
            var = tk.StringVar()
            e = tk.Entry(form, textvariable=var, font=(FONT, 10),
                         bg=WHITE, fg=DARK_TEXT, relief="solid", bd=1, width=35)
            e.grid(row=row_idx, column=1, sticky="ew", padx=(10, 0), pady=4)
            return var

        self._name_var    = lbl_entry("Full Name",  0, required=True)
        self._phone_var   = lbl_entry("Phone",      1)
        self._email_var   = lbl_entry("Email",      2)

        tk.Label(form, text="Address", font=(FONT, 10, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).grid(row=3, column=0, sticky="nw", pady=4)
        self._address = tk.Text(form, width=35, height=3, font=(FONT, 10),
                                bg=WHITE, fg=DARK_TEXT, relief="solid", bd=1)
        self._address.grid(row=3, column=1, sticky="ew", padx=(10, 0), pady=4)

        form.columnconfigure(1, weight=1)

        btn_frame = tk.Frame(self, bg=BG_COLOR)
        btn_frame.pack(pady=(4, 16))
        _make_btn(btn_frame, "Save", self._save, bg=MINT, fg=DARK_TEXT).pack(side="left", padx=8)
        _make_btn(btn_frame, "Cancel", self.destroy, bg=CORAL).pack(side="left", padx=8)

    def _populate(self, adopter):
        self._name_var.set(adopter.get("full_name", ""))
        self._phone_var.set(adopter.get("phone", ""))
        self._email_var.set(adopter.get("email", ""))
        self._address.insert("1.0", adopter.get("address", ""))

    def _validate_email(self, email):
        if not email:
            return True  # optional
        pattern = r'^[\w\.\+\-]+@[\w\-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _save(self):
        name    = self._name_var.get().strip()
        phone   = self._phone_var.get().strip()
        email   = self._email_var.get().strip()
        address = self._address.get("1.0", "end").strip()

        if not name:
            messagebox.showwarning("Validation", "Full Name is required.", parent=self)
            return
        if email and not self._validate_email(email):
            messagebox.showwarning("Validation",
                                   "Invalid email address format.", parent=self)
            return

        try:
            if self._adopter:
                db.update_adopter(
                    adopter_id=self._adopter["id"],
                    full_name=name, phone=phone,
                    email=email, address=address
                )
                messagebox.showinfo("Updated", "Adopter updated successfully!", parent=self)
            else:
                db.add_adopter(
                    full_name=name, phone=phone,
                    email=email, address=address,
                    date_registered=date.today().strftime("%d-%m-%Y")
                )
                messagebox.showinfo("Added", "Adopter added successfully!", parent=self)

            if self.on_save:
                self.on_save()
            self.destroy()

        except Exception as exc:
            messagebox.showerror("Error", f"Could not save:\n{exc}", parent=self)
