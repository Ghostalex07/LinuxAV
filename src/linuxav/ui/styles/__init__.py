from tkinter import ttk
from linuxav.ui.styles.theme import COLORS, FONTS, DIMENSIONS


def apply_theme():
    style = ttk.Style()
    style.theme_use("clam")

    style.configure("Dark.TFrame", background=COLORS["bg_primary"])
    style.configure("Dark.TLabel", background=COLORS["bg_primary"], foreground=COLORS["fg_primary"], font=FONTS["default"])
    style.configure("Dark.TLabelframe", background=COLORS["bg_primary"], foreground=COLORS["fg_primary"])
    style.configure("Dark.TLabelframe.Label", background=COLORS["bg_primary"], foreground=COLORS["fg_primary"])

    style.configure("Title.TLabel", background=COLORS["bg_primary"], foreground=COLORS["fg_accent"], font=FONTS["title"])

    style.configure("Dark.TButton", background=COLORS["bg_secondary"], foreground=COLORS["fg_primary"], bordercolor=COLORS["border"], font=FONTS["button"])
    style.map(
        "Dark.TButton",
        background=[("active", COLORS["fg_accent"])],
        foreground=[("active", COLORS["bg_primary"])],
        bordercolor=[("active", COLORS["fg_accent"])],
    )

    style.configure("Dark.Horizontal.TProgressbar", background=COLORS["fg_accent"], troughcolor=COLORS["bg_secondary"])
    style.configure("Dark.TProgressbar", background=COLORS["fg_accent"], troughcolor=COLORS["bg_secondary"])

    return style


def get_colors():
    return COLORS.copy()


def get_fonts():
    return FONTS.copy()


def get_dimensions():
    return DIMENSIONS.copy()
