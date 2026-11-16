"""
PawPal - Pet Management Module
Full CRUD interface for managing pets: list, search, filter, add, edit, delete.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

try:
    from PIL import Image, ImageTk
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

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

SPECIES_OPTIONS = ["All", "Dog", "Cat", "Rabbit", "Bird", "Fish", "Other"]
STATUS_OPTIONS  = ["All", "Available", "Adopted", "Pending"]
GENDER_OPTIONS  = ["Male", "Female", "Unknown"]


class PetsModule(tk.Frame):
    """Pet management screen with list, detail panel, and add/edit dialogs."""

    def __init__(self, parent, **kwargs):
        kwargs.setdefault("bg", BG_COLOR)
        super().__init__(parent, **kwargs)

        self._selected_pet_id  = None
        self._detail_photo     = None   # keep reference to avoid GC

        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        self._build_header()
        self._build_toolbar()
        self._build_main_area()
        self._apply_treeview_style()
        self.load_pets()

    # ── UI construction ──────────────────────────────────────────────────────

    def _build_header(self):
        hdr = tk.Frame(self, bg=BG_COLOR)
        hdr.grid(row=0, column=0, sticky="ew", padx=24, pady=(24, 4))

        tk.Label(hdr, text="Pet Management",
                 font=("Segoe UI", 26, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(anchor="w")

        tk.Label(hdr, text="Browse, add, edit, and remove pets from the system",
                 font=("Segoe UI", 12),
                 bg=BG_COLOR, fg="#6B7A8D").pack(anchor="w")

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG_COLOR)
        bar.grid(row=1, column=0, sticky="ew", padx=24, pady=8)

        # Search entry
        tk.Label(bar, text="Search:", font=("Segoe UI", 10),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left")

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.search_pets())
        search_entry = tk.Entry(bar, textvariable=self.search_var,
                                font=("Segoe UI", 10), width=22,
                                relief="solid", bd=1)
        search_entry.pack(side="left", padx=(4, 8), ipady=4)

        tk.Button(bar, text="🔍 Search", command=self.search_pets,
                  font=("Segoe UI", 10), bg=DARK_TEXT, fg=WHITE,
                  relief="flat", padx=10, pady=4,
                  cursor="hand2").pack(side="left", padx=(0, 16))

        # Species filter
        tk.Label(bar, text="Species:", font=("Segoe UI", 10),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left")
        self.species_filter = tk.StringVar(value="All")
        species_cb = ttk.Combobox(bar, textvariable=self.species_filter,
                                  values=SPECIES_OPTIONS, state="readonly",
                                  width=10, font=("Segoe UI", 10))
        species_cb.pack(side="left", padx=(4, 8))
        species_cb.bind("<<ComboboxSelected>>", lambda _: self.search_pets())

        # Status filter
        tk.Label(bar, text="Status:", font=("Segoe UI", 10),
                 bg=BG_COLOR, fg=DARK_TEXT).pack(side="left")
        self.status_filter = tk.StringVar(value="All")
        status_cb = ttk.Combobox(bar, textvariable=self.status_filter,
                                 values=STATUS_OPTIONS, state="readonly",
                                 width=12, font=("Segoe UI", 10))
        status_cb.pack(side="left", padx=(4, 16))
        status_cb.bind("<<ComboboxSelected>>", lambda _: self.search_pets())

        # Add button — right-aligned
        tk.Button(bar, text="➕  Add New Pet", command=self.open_add_dialog,
                  font=("Segoe UI", 10, "bold"),
                  bg=CORAL, fg=DARK_TEXT,
                  relief="flat", padx=14, pady=5,
                  cursor="hand2").pack(side="right")

    def _build_main_area(self):
        main = tk.Frame(self, bg=BG_COLOR)
        main.grid(row=2, column=0, sticky="nsew", padx=24, pady=(0, 16))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        # ── Left: treeview ────────────────────────────────────────────────
        list_frame = tk.Frame(main, bg=WHITE, relief="flat", bd=1)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        cols = ("ID", "Name", "Species", "Breed", "Age", "Gender", "Status")
        self.tree = ttk.Treeview(list_frame, columns=cols,
                                 show="headings", selectmode="browse")

        col_widths = {"ID": 40, "Name": 110, "Species": 80,
                      "Breed": 100, "Age": 45, "Gender": 65, "Status": 85}
        for col in cols:
            self.tree.heading(col, text=col,
                              command=lambda c=col: self._sort_by(c))
            self.tree.column(col, width=col_widths.get(col, 90),
                             anchor="center")

        vsb = ttk.Scrollbar(list_frame, orient="vertical",
                             command=self.tree.yview)
        hsb = ttk.Scrollbar(list_frame, orient="horizontal",
                             command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self.show_pet_detail)

        # Action buttons below list
        btn_row = tk.Frame(list_frame, bg=WHITE, pady=8)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="ew", padx=8)

        self.edit_btn = tk.Button(btn_row, text="✏️  Edit",
                                  command=self.open_edit_dialog,
                                  font=("Segoe UI", 10), bg=MINT,
                                  fg=DARK_TEXT, relief="flat",
                                  padx=14, pady=5, cursor="hand2")
        self.edit_btn.pack(side="left", padx=(0, 8))

        self.del_btn = tk.Button(btn_row, text="🗑️  Delete",
                                 command=self.delete_pet,
                                 font=("Segoe UI", 10), bg=CORAL,
                                 fg=DARK_TEXT, relief="flat",
                                 padx=14, pady=5, cursor="hand2")
        self.del_btn.pack(side="left")

        # ── Right: detail panel ───────────────────────────────────────────
        self.detail_frame = tk.Frame(main, bg=WHITE, relief="flat", bd=1)
        self.detail_frame.grid(row=0, column=1, sticky="nsew")
        self._build_detail_placeholder()

    def _build_detail_placeholder(self):
        """Show placeholder text when no pet is selected."""
        for w in self.detail_frame.winfo_children():
            w.destroy()
        tk.Label(self.detail_frame,
                 text="🐾\nSelect a pet\nto view details",
                 font=("Segoe UI", 13), bg=WHITE, fg="#BBBBBB",
                 justify="center").pack(expand=True)

    def _apply_treeview_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Pets.Treeview",
                        background=TABLE_ROW_ODD,
                        foreground=DARK_TEXT,
                        rowheight=30,
                        fieldbackground=TABLE_ROW_ODD,
                        font=("Segoe UI", 10))
        style.configure("Pets.Treeview.Heading",
                        background=TABLE_HEADER_BG,
                        foreground=TABLE_HEADER_FG,
                        font=("Segoe UI", 10, "bold"))
        style.map("Pets.Treeview",
                  background=[("selected", LAVENDER)])
        self.tree.configure(style="Pets.Treeview")
        self.tree.tag_configure("odd",       background=TABLE_ROW_ODD)
        self.tree.tag_configure("even",      background=TABLE_ROW_EVEN)
        self.tree.tag_configure("available", foreground=SUCCESS_COLOR)
        self.tree.tag_configure("adopted",   foreground=CORAL)
        self.tree.tag_configure("pending",   foreground="#B8860B")

    # ── Data loading ─────────────────────────────────────────────────────────

    def load_pets(self):
        """Load all pets from the database into the treeview."""
        self._selected_pet_id = None
        self._build_detail_placeholder()
        self.tree.delete(*self.tree.get_children())

        if not DB_AVAILABLE:
            return

        try:
            pets = db.get_all_pets()
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        self._populate_tree(pets)

    def _populate_tree(self, pets):
        self.tree.delete(*self.tree.get_children())
        for idx, pet in enumerate(pets):
            pid     = pet.get("pet_id", pet[0] if len(pet) > 0 else "") if hasattr(pet, "get") else (pet[0] if len(pet) > 0 else "")
            name    = pet.get("name", pet[1] if len(pet) > 1 else "") if hasattr(pet, "get") else (pet[1] if len(pet) > 1 else "")
            species = pet.get("species", pet[2] if len(pet) > 2 else "") if hasattr(pet, "get") else (pet[2] if len(pet) > 2 else "")
            breed   = pet.get("breed", pet[3] if len(pet) > 3 else "") if hasattr(pet, "get") else (pet[3] if len(pet) > 3 else "")
            age     = pet.get("age", pet[4] if len(pet) > 4 else "") if hasattr(pet, "get") else (pet[4] if len(pet) > 4 else "")
            gender  = pet.get("gender", pet[5] if len(pet) > 5 else "") if hasattr(pet, "get") else (pet[5] if len(pet) > 5 else "")
            status  = pet.get("status", pet[7] if len(pet) > 7 else "") if hasattr(pet, "get") else (pet[7] if len(pet) > 7 else "")

            row_tag  = "even" if idx % 2 == 0 else "odd"
            stat_tag = str(status).lower() if str(status).lower() in (
                "available", "adopted", "pending") else ""
            tags = (row_tag, stat_tag) if stat_tag else (row_tag,)

            self.tree.insert("", "end", iid=str(pid),
                             values=(pid, name, species, breed,
                                     age, gender, status),
                             tags=tags)

    def search_pets(self):
        """Filter pets by search text, species, and status."""
        query   = self.search_var.get().strip().lower()
        species = self.species_filter.get()
        status  = self.status_filter.get()

        if not DB_AVAILABLE:
            return

        try:
            pets = db.get_all_pets()
        except Exception as exc:
            messagebox.showerror("Database Error", str(exc))
            return

        filtered = []
        for pet in pets:
            name        = str(pet.get("name", pet[1] if len(pet) > 1 else "") if hasattr(pet, "get") else (pet[1] if len(pet) > 1 else "")).lower()
            pet_species = str(pet.get("species", pet[2] if len(pet) > 2 else "") if hasattr(pet, "get") else (pet[2] if len(pet) > 2 else ""))
            pet_status  = str(pet.get("status", pet[7] if len(pet) > 7 else "") if hasattr(pet, "get") else (pet[7] if len(pet) > 7 else ""))

            if query and query not in name and query not in pet_species.lower():
                continue
            if species != "All" and pet_species != species:
                continue
            if status != "All" and pet_status != status:
                continue
            filtered.append(pet)

        self._populate_tree(filtered)

    def show_pet_detail(self, event=None):
        """Display full details for the currently selected pet."""
        sel = self.tree.selection()
        if not sel:
            return

        pet_id = int(sel[0])
        self._selected_pet_id = pet_id

        pet = None
        if DB_AVAILABLE:
            try:
                pet = db.get_pet_by_id(pet_id)
            except Exception:
                pet = None

        if pet is None:
            # Fallback: read from treeview values
            vals = self.tree.item(sel[0], "values")
            pet  = vals

        self._render_detail(pet)

    def _render_detail(self, pet):
        """Rebuild the right-hand detail panel for *pet*."""
        for w in self.detail_frame.winfo_children():
            w.destroy()

        if not pet:
            self._build_detail_placeholder()
            return

        # Safely unpack — supports dict/Row get as well as tuple index
        def _get(key, idx=None, default="—"):
            if hasattr(pet, "get"):
                v = pet.get(key)
                if v not in (None, ""):
                    return str(v)
            if idx is not None:
                try:
                    v = pet[idx]
                    return str(v) if v not in (None, "") else default
                except (IndexError, TypeError):
                    pass
            return default

        pid         = _get("pet_id", 0)
        name        = _get("name", 1)
        species     = _get("species", 2)
        breed       = _get("breed", 3)
        age         = _get("age", 4)
        gender      = _get("gender", 5)
        description = _get("description", 6)
        color_coat  = _get("color", 7)
        status      = _get("status", 8)
        image_path  = pet.get("image_path") if hasattr(pet, "get") else (_get("image_path", 9, None))

        canvas = tk.Canvas(self.detail_frame, bg=WHITE,
                           highlightthickness=0)
        canvas.pack(fill="both", expand=True)

        scroll_frame = tk.Frame(canvas, bg=WHITE)
        scrollbar    = ttk.Scrollbar(canvas, orient="vertical",
                                     command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        win = canvas.create_window((0, 0), window=scroll_frame, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win, width=canvas.winfo_width())

        scroll_frame.bind("<Configure>", _on_configure)

        # Pet image
        img_label = tk.Label(scroll_frame, bg=WHITE)
        img_label.pack(pady=(16, 8))
        self._detail_photo = self._load_image(image_path, size=(150, 150),
                                              bg_color=CORAL,
                                              label=img_label)

        # Pet name
        tk.Label(scroll_frame, text=name,
                 font=("Segoe UI", 16, "bold"),
                 bg=WHITE, fg=DARK_TEXT).pack()

        # Status badge
        badge_colors = {
            "Available": (SUCCESS_COLOR, WHITE),
            "Adopted":   (CORAL,         DARK_TEXT),
            "Pending":   (YELLOW,        DARK_TEXT),
        }
        badge_bg, badge_fg = badge_colors.get(status, (BORDER_COLOR, DARK_TEXT))
        tk.Label(scroll_frame, text=f"  {status}  ",
                 font=("Segoe UI", 10, "bold"),
                 bg=badge_bg, fg=badge_fg,
                 relief="flat", padx=6, pady=2).pack(pady=(4, 12))

        # Attribute rows
        rows = [
            ("ID",          pid),
            ("Species",     species),
            ("Breed",       breed),
            ("Age",         f"{age} years" if age != "—" else "—"),
            ("Gender",      gender),
            ("Color/Coat",  color_coat),
            ("Description", description),
        ]
        for label_text, value in rows:
            row = tk.Frame(scroll_frame, bg=WHITE)
            row.pack(fill="x", padx=16, pady=3)
            tk.Label(row, text=f"{label_text}:", width=12,
                     font=("Segoe UI", 10, "bold"), bg=WHITE,
                     fg=DARK_TEXT, anchor="w").pack(side="left")
            tk.Label(row, text=value,
                     font=("Segoe UI", 10), bg=WHITE,
                     fg="#555555", anchor="w", wraplength=180,
                     justify="left").pack(side="left", padx=4)

        # Separator
        tk.Frame(scroll_frame, bg=BORDER_COLOR, height=1).pack(
            fill="x", padx=16, pady=8)

    # ── Image helper ─────────────────────────────────────────────────────────

    def _load_image(self, path, size=(150, 150),
                    bg_color=CORAL, label=None):
        """
        Load image from *path* at *size*, display in *label*.
        Falls back to a colored placeholder rectangle.
        Returns an ImageTk.PhotoImage (or None).
        """
        photo = None
        if PIL_AVAILABLE and path and path != "—":
            try:
                img = Image.open(path)
                img.thumbnail(size, Image.LANCZOS)
                # Paste onto white canvas of exact size
                canvas_img = Image.new("RGBA", size, (255, 255, 255, 0))
                offset = ((size[0] - img.size[0]) // 2,
                          (size[1] - img.size[1]) // 2)
                canvas_img.paste(img, offset)
                photo = ImageTk.PhotoImage(canvas_img)
            except Exception:
                photo = None

        if photo and label:
            label.config(image=photo, bg=WHITE)
        elif label:
            # Coloured placeholder
            placeholder = tk.Canvas(label.master, width=size[0],
                                    height=size[1], bg=bg_color,
                                    highlightthickness=0)
            placeholder.create_text(size[0] // 2, size[1] // 2,
                                    text="🐾", font=("Segoe UI", 32),
                                    fill=DARK_TEXT)
            placeholder.pack()
            label.destroy()

        return photo

    # ── Sort helper ──────────────────────────────────────────────────────────

    def _sort_by(self, col):
        """Toggle ascending/descending sort on a treeview column."""
        col_map = {"ID": 0, "Name": 1, "Species": 2, "Breed": 3,
                   "Age": 4, "Gender": 5, "Status": 6}
        idx = col_map.get(col, 1)
        items = [(self.tree.set(k, col), k)
                 for k in self.tree.get_children("")]
        reverse = getattr(self, f"_sort_rev_{col}", False)
        try:
            items.sort(key=lambda t: (int(t[0]) if col == "ID"
                                      else t[0].lower()), reverse=reverse)
        except ValueError:
            items.sort(key=lambda t: t[0].lower(), reverse=reverse)
        for order, (_, k) in enumerate(items):
            self.tree.move(k, "", order)
        setattr(self, f"_sort_rev_{col}", not reverse)

    # ── CRUD operations ──────────────────────────────────────────────────────

    def open_add_dialog(self):
        """Open the Toplevel dialog for adding a new pet."""
        _PetDialog(self, mode="add", on_save=self._after_save)

    def open_edit_dialog(self):
        """Open the Toplevel dialog for editing the selected pet."""
        if self._selected_pet_id is None:
            messagebox.showwarning("No Selection",
                                   "Please select a pet to edit.")
            return
        pet = None
        if DB_AVAILABLE:
            try:
                pet = db.get_pet_by_id(self._selected_pet_id)
            except Exception:
                pass
        if pet is None:
            # Fall back to treeview data
            sel = self.tree.selection()
            if sel:
                vals = self.tree.item(sel[0], "values")
                pet  = vals
        if pet is None:
            messagebox.showerror("Error", "Could not load pet data.")
            return
        _PetDialog(self, mode="edit", pet_data=pet, on_save=self._after_save)

    def delete_pet(self):
        """Confirm and delete the currently selected pet."""
        if self._selected_pet_id is None:
            messagebox.showwarning("No Selection",
                                   "Please select a pet to delete.")
            return

        sel = self.tree.selection()
        name = ""
        if sel:
            vals = self.tree.item(sel[0], "values")
            name = vals[1] if len(vals) > 1 else ""

        confirmed = messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to delete '{name}'?\n"
            "This action cannot be undone.",
            icon="warning",
        )
        if not confirmed:
            return

        if DB_AVAILABLE:
            try:
                db.delete_pet(self._selected_pet_id)
                messagebox.showinfo("Deleted",
                                    f"'{name}' has been removed.")
            except Exception as exc:
                messagebox.showerror("Error", str(exc))
                return
        else:
            # Remove from treeview only (no DB)
            if sel:
                self.tree.delete(sel[0])
            messagebox.showinfo("Deleted (Demo)", f"'{name}' removed.")
            return

        self._selected_pet_id = None
        self._build_detail_placeholder()
        self.load_pets()

    def _after_save(self):
        """Callback executed after a successful add or edit."""
        self.load_pets()

    def refresh(self):
        """Public method: reload all pets (callable from parent frame)."""
        self.search_var.set("")
        self.species_filter.set("All")
        self.status_filter.set("All")
        self.load_pets()


# ── Add / Edit dialog ────────────────────────────────────────────────────────

class _PetDialog(tk.Toplevel):
    """Modal Toplevel window for adding or editing a pet."""

    SPECIES_VALUES = ["Dog", "Cat", "Rabbit", "Bird", "Fish", "Other"]
    STATUS_VALUES  = ["Available", "Adopted", "Pending"]
    GENDER_VALUES  = ["Male", "Female", "Unknown"]

    def __init__(self, parent, mode="add", pet_data=None, on_save=None):
        super().__init__(parent)
        self.mode       = mode
        self.pet_data   = pet_data or []
        self.on_save    = on_save
        self._img_path  = ""
        self._preview_photo = None

        self.title("Add New Pet" if mode == "add" else "Edit Pet")
        self.resizable(False, False)
        self.configure(bg=BG_COLOR)
        self.grab_set()   # modal

        self._build_form()
        if mode == "edit":
            self._populate_fields()

        # Centre over parent
        self.update_idletasks()
        pw = parent.winfo_rootx()
        py = parent.winfo_rooty()
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"{w}x{h}+{pw + 60}+{py + 40}")

    # ── Form construction ────────────────────────────────────────────────────

    def _build_form(self):
        self.columnconfigure(0, weight=1)

        # Title bar
        title_text = "Add New Pet" if self.mode == "add" else "Edit Pet"
        tk.Label(self, text=title_text,
                 font=("Segoe UI", 15, "bold"),
                 bg=BG_COLOR, fg=DARK_TEXT,
                 pady=14).grid(row=0, column=0, columnspan=2, sticky="ew",
                               padx=20)

        # Two-column layout
        form = tk.Frame(self, bg=BG_COLOR)
        form.grid(row=1, column=0, sticky="nsew", padx=20, pady=4)
        form.columnconfigure(1, weight=1)

        def lbl(row, text, req=False):
            suffix = " *" if req else ""
            tk.Label(form, text=f"{text}{suffix}",
                     font=("Segoe UI", 10),
                     bg=BG_COLOR, fg=DARK_TEXT,
                     anchor="e", width=14).grid(
                row=row, column=0, sticky="e", padx=(0, 8), pady=5)

        # Name *
        lbl(0, "Name", req=True)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var,
                 font=("Segoe UI", 10), relief="solid", bd=1,
                 width=28).grid(row=0, column=1, sticky="ew", pady=5)

        # Species *
        lbl(1, "Species", req=True)
        self.species_var = tk.StringVar(value=self.SPECIES_VALUES[0])
        ttk.Combobox(form, textvariable=self.species_var,
                     values=self.SPECIES_VALUES, state="readonly",
                     font=("Segoe UI", 10), width=26).grid(
            row=1, column=1, sticky="ew", pady=5)

        # Breed
        lbl(2, "Breed")
        self.breed_var = tk.StringVar()
        tk.Entry(form, textvariable=self.breed_var,
                 font=("Segoe UI", 10), relief="solid", bd=1,
                 width=28).grid(row=2, column=1, sticky="ew", pady=5)

        # Age
        lbl(3, "Age (years)")
        self.age_var = tk.StringVar()
        tk.Entry(form, textvariable=self.age_var,
                 font=("Segoe UI", 10), relief="solid", bd=1,
                 width=28).grid(row=3, column=1, sticky="ew", pady=5)

        # Gender
        lbl(4, "Gender")
        self.gender_var = tk.StringVar(value=self.GENDER_VALUES[0])
        ttk.Combobox(form, textvariable=self.gender_var,
                     values=self.GENDER_VALUES, state="readonly",
                     font=("Segoe UI", 10), width=26).grid(
            row=4, column=1, sticky="ew", pady=5)

        # Color / Coat
        lbl(5, "Color / Coat")
        self.color_var = tk.StringVar()
        tk.Entry(form, textvariable=self.color_var,
                 font=("Segoe UI", 10), relief="solid", bd=1,
                 width=28).grid(row=5, column=1, sticky="ew", pady=5)

        # Status
        lbl(6, "Status")
        self.status_var = tk.StringVar(value=self.STATUS_VALUES[0])
        ttk.Combobox(form, textvariable=self.status_var,
                     values=self.STATUS_VALUES, state="readonly",
                     font=("Segoe UI", 10), width=26).grid(
            row=6, column=1, sticky="ew", pady=5)

        # Description
        lbl(7, "Description")
        self.desc_text = tk.Text(form, font=("Segoe UI", 10),
                                 width=28, height=4,
                                 relief="solid", bd=1, wrap="word")
        self.desc_text.grid(row=7, column=1, sticky="ew", pady=5)

        # Image
        lbl(8, "Image")
        img_row = tk.Frame(form, bg=BG_COLOR)
        img_row.grid(row=8, column=1, sticky="ew", pady=5)

        self.img_path_var = tk.StringVar(value="No image selected")
        tk.Label(img_row, textvariable=self.img_path_var,
                 font=("Segoe UI", 9), bg=BG_COLOR, fg="#888888",
                 wraplength=180, justify="left").pack(side="left")
        tk.Button(img_row, text="Browse…",
                  command=self._browse_image,
                  font=("Segoe UI", 9), bg=MINT, fg=DARK_TEXT,
                  relief="flat", padx=8, cursor="hand2").pack(side="right")

        # Image preview
        self.preview_label = tk.Label(self, bg=BG_COLOR)
        self.preview_label.grid(row=2, column=0, pady=(4, 0))

        # Feedback label
        self.feedback_var = tk.StringVar()
        self.feedback_lbl = tk.Label(self, textvariable=self.feedback_var,
                                     font=("Segoe UI", 10),
                                     bg=BG_COLOR, fg=ERROR_COLOR)
        self.feedback_lbl.grid(row=3, column=0, pady=(4, 0))

        # Buttons
        btn_row = tk.Frame(self, bg=BG_COLOR)
        btn_row.grid(row=4, column=0, sticky="ew",
                     padx=20, pady=(10, 16))

        tk.Button(btn_row, text="💾  Save",
                  command=self._save,
                  font=("Segoe UI", 11, "bold"),
                  bg=SUCCESS_COLOR, fg=WHITE,
                  relief="flat", padx=18, pady=7,
                  cursor="hand2").pack(side="left", padx=(0, 10))

        tk.Button(btn_row, text="Cancel",
                  command=self.destroy,
                  font=("Segoe UI", 11),
                  bg=BORDER_COLOR, fg=DARK_TEXT,
                  relief="flat", padx=18, pady=7,
                  cursor="hand2").pack(side="left")

    # ── Populate for edit mode ────────────────────────────────────────────────

    def _populate_fields(self):
        """Pre-fill form fields with existing pet data."""
        def _get(key, idx=None, default=""):
            if hasattr(self.pet_data, "get"):
                v = self.pet_data.get(key)
                if v not in (None, ""):
                    return str(v)
            if idx is not None:
                try:
                    v = self.pet_data[idx]
                    return str(v) if v not in (None, "") else default
                except (IndexError, TypeError):
                    pass
            return default

        self.name_var.set(_get("name", 1))
        species = _get("species", 2)
        if species in self.SPECIES_VALUES:
            self.species_var.set(species)
        self.breed_var.set(_get("breed", 3))
        self.age_var.set(_get("age", 4))
        gender = _get("gender", 5)
        if gender in self.GENDER_VALUES:
            self.gender_var.set(gender)
        self.desc_text.insert("1.0", _get("description", 6))
        self.color_var.set(_get("color", 7))
        status = _get("status", 8)
        if status in self.STATUS_VALUES:
            self.status_var.set(status)
        img_path = self.pet_data.get("image_path") if hasattr(self.pet_data, "get") else None
        if not img_path:
            img_path = _get("image_path", 9)
        if img_path:
            self._img_path = img_path
            self.img_path_var.set(Path(img_path).name)
            self._update_preview(img_path)

    # ── Image browser ─────────────────────────────────────────────────────────

    def _browse_image(self):
        path = filedialog.askopenfilename(
            title="Select Pet Image",
            filetypes=[
                ("Image files", "*.png *.jpg *.jpeg *.gif *.bmp *.webp"),
                ("All files", "*.*"),
            ],
        )
        if path:
            self._img_path = path
            self.img_path_var.set(Path(path).name)
            self._update_preview(path)

    def _update_preview(self, path):
        if not PIL_AVAILABLE:
            return
        try:
            img = Image.open(path)
            img.thumbnail((100, 100), Image.LANCZOS)
            self._preview_photo = ImageTk.PhotoImage(img)
            self.preview_label.config(image=self._preview_photo, bg=BG_COLOR)
        except Exception:
            self.preview_label.config(text="Preview unavailable",
                                      font=("Segoe UI", 9),
                                      bg=BG_COLOR, fg="#888888")

    # ── Save ──────────────────────────────────────────────────────────────────

    def _save(self):
        name    = self.name_var.get().strip()
        species = self.species_var.get().strip()

        # Validation
        errors = []
        if not name:
            errors.append("Name is required.")
        if not species:
            errors.append("Species is required.")
        age_val = self.age_var.get().strip()
        if age_val:
            try:
                age_float = float(age_val)
                if age_float < 0:
                    errors.append("Age must be a positive number.")
            except ValueError:
                errors.append("Age must be a valid number.")
        else:
            age_float = None

        if errors:
            self.feedback_var.set("\n".join(errors))
            self.feedback_lbl.config(fg=ERROR_COLOR)
            return

        pet_payload = {
            "name":        name,
            "species":     species,
            "breed":       self.breed_var.get().strip() or None,
            "age":         age_float,
            "gender":      self.gender_var.get(),
            "description": self.desc_text.get("1.0", "end").strip() or None,
            "color":       self.color_var.get().strip() or None,
            "status":      self.status_var.get(),
            "image_path":  self._img_path or None,
        }

        if DB_AVAILABLE:
            try:
                if self.mode == "add":
                    db.add_pet(**pet_payload)
                else:
                    pet_id = int(self.pet_data[0])
                    db.update_pet(pet_id, **pet_payload)
            except Exception as exc:
                self.feedback_var.set(f"Error: {exc}")
                self.feedback_lbl.config(fg=ERROR_COLOR)
                return

        action = "added" if self.mode == "add" else "updated"
        messagebox.showinfo("Success", f"Pet '{name}' has been {action}.")

        if callable(self.on_save):
            self.on_save()

        self.destroy()
