"""
ui/components.py — Reusable Tkinter widget library for PawPal.

All widgets are built on standard Tkinter (no third-party CTk required).
Import this module and instantiate the classes as you would any tk widget.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from ui.theme import (
    CORAL, MINT, WHITE, DARK_TEXT, BG_COLOR,
    BUTTON_HOVER, INPUT_BG, INPUT_BORDER, BORDER_COLOR,
    TABLE_HEADER_BG, TABLE_HEADER_FG, TABLE_ROW_ODD, TABLE_ROW_EVEN,
    FONT_BODY, FONT_BUTTON, FONT_SMALL, FONT_SUBHEADING,
    PADDING,
)

# ---------------------------------------------------------------------------
# Try to import Pillow; fall back gracefully if not installed.
# ---------------------------------------------------------------------------
try:
    from PIL import Image, ImageTk
    _PIL_AVAILABLE = True
except ImportError:
    _PIL_AVAILABLE = False


# ===========================================================================
# 1. RoundedButton
# ===========================================================================

class RoundedButton(tk.Button):
    """
    A flat-styled button with configurable colours and hover effects.

    Parameters
    ----------
    parent     : tk widget
    text       : button label
    command    : callable
    bg_color   : background colour (default CORAL)
    fg_color   : foreground / text colour (default WHITE)
    width      : approximate character width
    **kwargs   : forwarded to tk.Button
    """

    def __init__(self, parent, text: str, command=None,
                 bg_color: str = CORAL, fg_color: str = WHITE,
                 width: int = 120, **kwargs):
        # Remove width from kwargs if accidentally duplicated
        kwargs.pop("width", None)

        super().__init__(
            parent,
            text=text,
            command=command,
            bg=bg_color,
            fg=fg_color,
            activebackground=BUTTON_HOVER,
            activeforeground=WHITE,
            relief=tk.FLAT,
            bd=0,
            padx=PADDING["medium"],
            pady=PADDING["small"],
            font=FONT_BUTTON,
            cursor="hand2",
            width=width // 10,   # tk width is in characters
            **kwargs,
        )

        self._bg_color  = bg_color
        self._hover_color = BUTTON_HOVER

        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    # ------------------------------------------------------------------
    def _on_enter(self, _event=None):
        self.config(bg=self._hover_color)

    def _on_leave(self, _event=None):
        self.config(bg=self._bg_color)


# ===========================================================================
# 2. StyledEntry
# ===========================================================================

class StyledEntry(tk.Frame):
    """
    A labelled entry that simulates placeholder text.

    Methods
    -------
    get()           → str
    set(value)
    delete(0, END)  — mirrors the tk.Entry API
    """

    def __init__(self, parent, placeholder: str = "", width: int = 200, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", INPUT_BG), **kwargs)

        self._placeholder = placeholder
        self._showing_placeholder = False

        self._entry = tk.Entry(
            self,
            font=FONT_BODY,
            bg=INPUT_BG,
            fg=DARK_TEXT,
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=INPUT_BORDER,
            highlightcolor=CORAL,
            width=width // 8,   # character units
            insertbackground=DARK_TEXT,
        )
        self._entry.pack(fill=tk.BOTH, expand=True, ipady=4)

        self._entry.bind("<FocusIn>",  self._on_focus_in)
        self._entry.bind("<FocusOut>", self._on_focus_out)

        # Show placeholder initially
        self._show_placeholder()

    # ------------------------------------------------------------------
    def _show_placeholder(self):
        self._entry.delete(0, tk.END)
        self._entry.insert(0, self._placeholder)
        self._entry.config(fg="#A0A0A0")
        self._showing_placeholder = True

    def _clear_placeholder(self):
        if self._showing_placeholder:
            self._entry.delete(0, tk.END)
            self._entry.config(fg=DARK_TEXT)
            self._showing_placeholder = False

    def _on_focus_in(self, _event=None):
        self._clear_placeholder()

    def _on_focus_out(self, _event=None):
        if not self._entry.get():
            self._show_placeholder()

    # ------------------------------------------------------------------
    # Public API mirroring tk.Entry
    # ------------------------------------------------------------------
    def get(self) -> str:
        """Return current value (empty string when only placeholder is shown)."""
        if self._showing_placeholder:
            return ""
        return self._entry.get()

    def set(self, value: str):
        """Replace the entry contents with *value*."""
        self._clear_placeholder()
        self._entry.delete(0, tk.END)
        self._entry.insert(0, value)
        if not value:
            self._show_placeholder()

    def delete(self, start, end):
        """Mirrors the tk.Entry.delete interface."""
        self._entry.delete(start, end)
        if not self._entry.get():
            self._show_placeholder()


# ===========================================================================
# 3. StyledCombobox
# ===========================================================================

class StyledCombobox(tk.Frame):
    """
    A ttk.Combobox wrapped in a Frame for uniform styling.

    Methods
    -------
    get()       → str
    set(value)
    """

    def __init__(self, parent, values: list = None, width: int = 20, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", BG_COLOR), **kwargs)

        self._var    = tk.StringVar()
        self._combo  = ttk.Combobox(
            self,
            textvariable=self._var,
            values=values or [],
            width=width,
            font=FONT_BODY,
            state="readonly",
        )
        self._combo.pack(fill=tk.BOTH, expand=True)

        # Style the combobox via ttk.Style
        style = ttk.Style()
        style.configure("PawPal.TCombobox",
                        fieldbackground=INPUT_BG,
                        background=INPUT_BG,
                        foreground=DARK_TEXT,
                        selectbackground=CORAL,
                        selectforeground=WHITE)
        self._combo.configure(style="PawPal.TCombobox")

    # ------------------------------------------------------------------
    def get(self) -> str:
        return self._var.get()

    def set(self, value: str):
        self._var.set(value)

    def configure_values(self, values: list):
        """Update the dropdown options at runtime."""
        self._combo.configure(values=values)


# ===========================================================================
# 4. CardFrame
# ===========================================================================

class CardFrame(tk.Frame):
    """
    A flat frame styled as a card (white background, subtle border).

    Parameters
    ----------
    parent   : tk widget
    bg_color : card background colour (default WHITE)
    """

    def __init__(self, parent, bg_color: str = WHITE, **kwargs):
        padx = kwargs.pop("padx", PADDING["medium"])
        pady = kwargs.pop("pady", PADDING["medium"])
        super().__init__(
            parent,
            bg=bg_color,
            relief=tk.FLAT,
            padx=padx,
            pady=pady,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            **kwargs,
        )


# ===========================================================================
# 5. StatCard
# ===========================================================================

class StatCard(tk.Frame):
    """
    A coloured dashboard stat card showing a large numeric value and a title.

    Parameters
    ----------
    parent : tk widget
    title  : str  — label beneath the value
    value  : str  — the number / stat to display (can be updated later)
    color  : str  — card background colour
    icon   : str  — optional emoji/text prefix shown above value

    Methods
    -------
    update(value)  — refresh the displayed value
    """

    def __init__(self, parent, title: str, value: str,
                 color: str = CORAL, icon: str = "", **kwargs):
        super().__init__(
            parent,
            bg=color,
            relief=tk.FLAT,
            padx=PADDING["large"],
            pady=PADDING["large"],
            **kwargs,
        )

        if icon:
            tk.Label(self, text=icon, font=("Segoe UI", 22),
                     bg=color, fg=WHITE).pack()

        self._value_var = tk.StringVar(value=str(value))
        tk.Label(self,
                 textvariable=self._value_var,
                 font=("Segoe UI", 28, "bold"),
                 bg=color,
                 fg=WHITE).pack()

        tk.Label(self,
                 text=title,
                 font=("Segoe UI", 11),
                 bg=color,
                 fg=WHITE).pack()

    # ------------------------------------------------------------------
    def update(self, value):
        """Update the displayed value."""
        self._value_var.set(str(value))


# ===========================================================================
# 6. SectionHeader
# ===========================================================================

class SectionHeader(tk.Frame):
    """
    A coloured header bar containing a section title.

    Parameters
    ----------
    parent   : tk widget
    title    : str
    bg_color : bar colour (default CORAL)
    """

    def __init__(self, parent, title: str, bg_color: str = CORAL, **kwargs):
        super().__init__(parent, bg=bg_color, **kwargs)

        tk.Label(
            self,
            text=title,
            font=FONT_SUBHEADING,
            bg=bg_color,
            fg=WHITE,
            padx=PADDING["medium"],
            pady=PADDING["small"],
        ).pack(anchor="w")


# ===========================================================================
# 7. StyledTreeview
# ===========================================================================

class StyledTreeview(tk.Frame):
    """
    A ttk.Treeview with vertical & horizontal scrollbars, styled headers,
    and alternating row colours.

    Parameters
    ----------
    parent   : tk widget
    columns  : list[str]  — internal column ids
    headings : list[str]  — display heading strings (same length as columns)

    Methods
    -------
    insert_row(values)   — append a row; returns the item id
    clear()              — remove all rows
    get_selected()       — returns (item_id, values_dict) or (None, None)
    delete_selected()    — removes the currently selected row
    """

    def __init__(self, parent, columns: list, headings: list, **kwargs):
        super().__init__(parent, bg=BG_COLOR, **kwargs)

        self._columns  = columns
        self._headings = headings

        # Apply ttk styles
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("PawPal.Treeview",
                        background=TABLE_ROW_ODD,
                        foreground=DARK_TEXT,
                        rowheight=28,
                        fieldbackground=TABLE_ROW_ODD,
                        font=FONT_BODY)
        style.configure("PawPal.Treeview.Heading",
                        background=TABLE_HEADER_BG,
                        foreground=TABLE_HEADER_FG,
                        font=("Segoe UI", 11, "bold"),
                        relief=tk.FLAT)
        style.map("PawPal.Treeview.Heading",
                  background=[("active", CORAL)])
        style.map("PawPal.Treeview",
                  background=[("selected", CORAL)],
                  foreground=[("selected", WHITE)])

        # Scrollbars
        self._vsb = ttk.Scrollbar(self, orient=tk.VERTICAL)
        self._hsb = ttk.Scrollbar(self, orient=tk.HORIZONTAL)

        self._tree = ttk.Treeview(
            self,
            columns=columns,
            show="headings",
            style="PawPal.Treeview",
            yscrollcommand=self._vsb.set,
            xscrollcommand=self._hsb.set,
        )
        self._vsb.config(command=self._tree.yview)
        self._hsb.config(command=self._tree.xview)

        # Layout
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._hsb.grid(row=1, column=0, sticky="ew")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Configure headings & column widths
        for col, heading in zip(columns, headings):
            self._tree.heading(col, text=heading,
                               command=lambda c=col: self._sort_by(c, False))
            self._tree.column(col, anchor=tk.CENTER, width=120, minwidth=60)

        # Alternating row colours via tags
        self._tree.tag_configure("odd",  background=TABLE_ROW_ODD)
        self._tree.tag_configure("even", background=TABLE_ROW_EVEN)

        self._row_count = 0

    # ------------------------------------------------------------------
    def _sort_by(self, col: str, descending: bool):
        """Sort tree contents when a heading is clicked."""
        data = [(self._tree.set(child, col), child)
                for child in self._tree.get_children("")]
        try:
            data.sort(key=lambda t: float(t[0]), reverse=descending)
        except ValueError:
            data.sort(key=lambda t: t[0].lower(), reverse=descending)

        for idx, (_, child) in enumerate(data):
            self._tree.move(child, "", idx)

        # Flip direction next click
        self._tree.heading(col,
                           command=lambda: self._sort_by(col, not descending))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def insert_row(self, values: list) -> str:
        """Append a row to the treeview; returns the item id."""
        tag   = "even" if self._row_count % 2 == 0 else "odd"
        iid   = self._tree.insert("", tk.END, values=values, tags=(tag,))
        self._row_count += 1
        return iid

    def clear(self):
        """Remove every row from the treeview."""
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._row_count = 0

    def get_selected(self):
        """
        Return (item_id, values_dict) for the selected row,
        or (None, None) if nothing is selected.
        """
        sel = self._tree.selection()
        if not sel:
            return None, None
        iid    = sel[0]
        values = self._tree.item(iid, "values")
        return iid, dict(zip(self._columns, values))

    def delete_selected(self):
        """Delete the currently selected row."""
        iid, _ = self.get_selected()
        if iid:
            self._tree.delete(iid)


# ===========================================================================
# 8. MessageDialog
# ===========================================================================

class MessageDialog:
    """Static factory for themed message dialogs."""

    @staticmethod
    def show_success(parent, message: str):
        messagebox.showinfo("Success ✓", message, parent=parent)

    @staticmethod
    def show_error(parent, message: str):
        messagebox.showerror("Error ✗", message, parent=parent)

    @staticmethod
    def show_warning(parent, message: str):
        messagebox.showwarning("Warning ⚠", message, parent=parent)

    @staticmethod
    def ask_confirm(parent, message: str) -> bool:
        """Return True if the user clicks OK / Yes."""
        return messagebox.askyesno("Confirm", message, parent=parent)


# ===========================================================================
# 9. SearchBar
# ===========================================================================

class SearchBar(tk.Frame):
    """
    A compact search entry + button widget.

    Parameters
    ----------
    parent      : tk widget
    placeholder : str
    command     : callable — called with the search string as argument

    Methods
    -------
    get()  → str
    """

    def __init__(self, parent, placeholder: str = "Search...",
                 command=None, **kwargs):
        super().__init__(parent, bg=kwargs.pop("bg", BG_COLOR), **kwargs)

        self._command = command

        self._entry = StyledEntry(self, placeholder=placeholder, width=240)
        self._entry.pack(side=tk.LEFT, padx=(0, PADDING["small"]))

        self._btn = RoundedButton(
            self,
            text="🔍 Search",
            command=self._on_search,
            bg_color=CORAL,
            width=90,
        )
        self._btn.pack(side=tk.LEFT)

        # Allow Enter key to trigger search
        self._entry._entry.bind("<Return>", lambda _e: self._on_search())

    # ------------------------------------------------------------------
    def _on_search(self):
        if self._command:
            self._command(self._entry.get())

    def get(self) -> str:
        return self._entry.get()

    def clear(self):
        self._entry.set("")


# ===========================================================================
# 10. ImageViewer
# ===========================================================================

class ImageViewer(tk.Label):
    """
    A Label that displays a resized image loaded from disk.

    Falls back to a placeholder text label when Pillow is unavailable
    or the image path is invalid / missing.

    Parameters
    ----------
    parent : tk widget
    size   : (width, height) in pixels (default 150×150)

    Methods
    -------
    load_image(path)  — load and display the image at *path*
    """

    def __init__(self, parent, size: tuple = (150, 150), **kwargs):
        bg = kwargs.pop("bg", WHITE)
        super().__init__(
            parent,
            bg=bg,
            relief=tk.FLAT,
            bd=1,
            highlightthickness=1,
            highlightbackground=BORDER_COLOR,
            **kwargs,
        )
        self._size    = size
        self._photo   = None          # keep a reference to prevent GC
        self._show_placeholder()

    # ------------------------------------------------------------------
    def _show_placeholder(self):
        self.config(
            image="",
            text="🐾\nNo Image",
            compound=tk.CENTER,
            font=FONT_BODY,
            fg="#A0A0A0",
            width=self._size[0] // 8,
            height=self._size[1] // 20,
        )

    # ------------------------------------------------------------------
    def load_image(self, path: str):
        """
        Load the image at *path*, resize it to self._size, and display it.
        Shows placeholder on any error.
        """
        if not path:
            self._show_placeholder()
            return

        if not _PIL_AVAILABLE:
            self.config(text="PIL not\ninstalled", image="", fg="#A0A0A0")
            return

        try:
            img          = Image.open(path)
            img          = img.resize(self._size, Image.LANCZOS)
            self._photo  = ImageTk.PhotoImage(img)
            self.config(image=self._photo, text="", width=self._size[0],
                        height=self._size[1])
        except Exception:
            self._show_placeholder()
