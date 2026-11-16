"""
ui/theme.py — PawPal visual theme constants.

Import specific names or use `from ui.theme import *` to pull everything
into a module's namespace.
"""

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
BG_COLOR        = "#FFF9F2"   # Warm off-white app background
CORAL           = "#F7B8A5"   # Primary accent
MINT            = "#B8E0D2"   # Secondary accent
LAVENDER        = "#D8C8F0"   # Tertiary accent
YELLOW          = "#FFF0C2"   # Highlight / warning tint
DARK_TEXT       = "#39434F"   # Main body text
WHITE           = "#FFFFFF"

# Sidebar
SIDEBAR_BG      = "#39434F"
SIDEBAR_TEXT    = "#FFFFFF"
SIDEBAR_HOVER   = "#F7B8A5"
SIDEBAR_ACTIVE  = "#F7B8A5"

# Status / feedback
SUCCESS_COLOR   = "#4CAF50"
ERROR_COLOR     = "#F44336"
WARNING_COLOR   = "#FF9800"

# Cards / layout
CARD_SHADOW     = "#E8E0D8"
BORDER_COLOR    = "#E0D8D0"

# Table
TABLE_ROW_ODD   = "#FFF9F2"
TABLE_ROW_EVEN  = "#F5F0EA"
TABLE_HEADER_BG = "#39434F"
TABLE_HEADER_FG = "#FFFFFF"

# Interaction
BUTTON_HOVER    = "#F0A090"
INPUT_BG        = "#FFFFFF"
INPUT_BORDER    = "#D0C8C0"

# ---------------------------------------------------------------------------
# Typography  (name, size[, weight])
# ---------------------------------------------------------------------------
FONT_TITLE          = ("Segoe UI", 24, "bold")
FONT_HEADING        = ("Segoe UI", 16, "bold")
FONT_SUBHEADING     = ("Segoe UI", 13, "bold")
FONT_BODY           = ("Segoe UI", 11)
FONT_SMALL          = ("Segoe UI",  9)
FONT_BUTTON         = ("Segoe UI", 11, "bold")
FONT_SIDEBAR        = ("Segoe UI", 12)
FONT_SIDEBAR_HEADER = ("Segoe UI", 14, "bold")

# ---------------------------------------------------------------------------
# Spacing & geometry
# ---------------------------------------------------------------------------
PADDING = {
    "small":  5,
    "medium": 10,
    "large":  20,
    "xlarge": 30,
}

BORDER_RADIUS = 10
CARD_WIDTH    = 200
