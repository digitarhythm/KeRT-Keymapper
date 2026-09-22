# SPDX-License-Identifier: GPL-2.0-or-later
"""This fork's own themes, registered without editing upstream's themes.py
(see docs/rebranding-plan.md section 6 and docs/theme-flat-keys-spec.md)."""

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleFactory

import key_style
import themes

DEFAULT_THEME = "KeRT Light"

# light themes: the inner part of a masked key is drawn only slightly lighter than the key
LIGHT_THEME_NAMES = {"KeRT Light"}

BRAND_THEMES = [
    (DEFAULT_THEME, {
        QPalette.Window: "#f5f6f8",
        QPalette.WindowText: "#1f2328",
        QPalette.Base: "#ffffff",
        QPalette.AlternateBase: "#f5f6f8",
        QPalette.ToolTipBase: "#ffffff",
        QPalette.ToolTipText: "#1f2328",
        QPalette.Text: "#1f2328",
        QPalette.Button: "#ffffff",           # key body
        QPalette.ButtonText: "#1f2328",       # key legend
        QPalette.Mid: "#303030",              # key outline, widget borders
        QPalette.BrightText: "#d1242f",
        QPalette.Link: "#0969da",
        QPalette.Highlight: "#00a3a3",        # brand colour (selection / pressed), provisional
        QPalette.HighlightedText: "#ffffff",
        (QPalette.Active, QPalette.Button): "#ffffff",
        (QPalette.Disabled, QPalette.ButtonText): "#9aa0a6",
        (QPalette.Disabled, QPalette.WindowText): "#9aa0a6",
        (QPalette.Disabled, QPalette.Text): "#9aa0a6",
        (QPalette.Disabled, QPalette.Light): "#ffffff",
    }),
]

_registered = False

# spacing between widgets and layout margins, in pixels (same as the line width)
LAYOUT_SPACING = 3
# left padding of the keyboard selector's text (stylesheet and DeviceComboBox share it)
COMBOBOX_PADDING_LEFT = 32
# check mark drawn over the highlighted background of a checked checkbox (resource "check.svg");
# set_check_image() stores its absolute path, the stylesheet references it. None = background only.
CHECK_IMAGE = None


def set_check_image(path):
    global CHECK_IMAGE
    CHECK_IMAGE = path.replace("\\", "/") if path else None


class BrandStyle(QProxyStyle):
    """Fusion with tight layouts: every layout margin and spacing is LAYOUT_SPACING."""

    _METRICS = (QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutTopMargin, QStyle.PM_LayoutRightMargin,
                QStyle.PM_LayoutBottomMargin, QStyle.PM_LayoutHorizontalSpacing, QStyle.PM_LayoutVerticalSpacing,
                QStyle.PM_DefaultLayoutSpacing)

    def pixelMetric(self, metric, option=None, widget=None):
        if metric in self._METRICS:
            return LAYOUT_SPACING
        return super().pixelMetric(metric, option, widget)

    def layoutSpacing(self, control1, control2, orientation, option=None, widget=None):
        return LAYOUT_SPACING


def resolve_theme(saved):
    """KeRT Light is the only theme: whatever was saved (an upstream theme name from before the
    rebranding, "System", nothing) resolves to it."""
    return DEFAULT_THEME


def stylesheet(name):
    """Application stylesheet for one of our themes: every box gets the same rounded corners and
    line width as the keys. Empty for other themes so upstream's look is untouched."""
    if name not in {n for n, _ in BRAND_THEMES}:
        return ""
    colors = dict(BRAND_THEMES)[name]
    mid = colors[QPalette.Mid]
    r = key_style.CORNER_RADIUS
    w = key_style.OUTLINE_WIDTH
    return """
        QPushButton, QToolButton, QComboBox, QSpinBox, QLineEdit, QTextEdit, QPlainTextEdit,
        QScrollArea, QTabWidget::pane, QGroupBox, EntryCard, EntryCardButton {{
            border: {w}px solid {mid};
            border-radius: {r}px;
            padding: 3px 8px;
        }}
        QToolButton {{
            padding: 1px 4px;
        }}
        /* keyboard selector: twice the usual space in front of the keyboard name */
        QComboBox {{
            padding-left: {pl}px;
        }}
        /* keycode picker buttons are sized from the font alone: no inner padding, or labels get clipped */
        SquareButton {{
            padding: 0px;
        }}
        QPushButton:pressed, QToolButton:pressed, EntryCardButton:pressed,
        QPushButton:checked, QToolButton:checked {{
            background-color: {hl};
            color: {hlt};
            border-color: {hl};
        }}
        QTabWidget#editor_tabs::tab-bar, QTabWidget#picker_tabs::tab-bar {{
            alignment: center;
        }}
        QTabBar::tab {{
            border: {w}px solid {mid};
            border-bottom: none;
            border-top-left-radius: {r}px;
            border-top-right-radius: {r}px;
            padding: 4px 12px;
            margin-right: 3px;
        }}
        QTabBar::tab:selected {{
            background-color: {hl};
            color: {hlt};
            border-color: {hl};
        }}
        QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
            border: none;
        }}
        QCheckBox::indicator, QGroupBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {mid};
            border-radius: 4px;
            background-color: {base};
        }}
        QCheckBox::indicator:checked, QGroupBox::indicator:checked {{
            background-color: {hl};
            border-color: {hl};{check}
        }}
        QCheckBox::indicator:disabled, QGroupBox::indicator:disabled {{
            border-color: {disabled};
        }}
        QToolTip {{
            border: {w}px solid {mid};
            border-radius: {r}px;
            padding: 4px;
        }}
    """.format(w=w, mid=mid, r=r, pl=COMBOBOX_PADDING_LEFT, hl=colors[QPalette.Highlight], hlt=colors[QPalette.HighlightedText],
               base=colors[QPalette.Base], disabled=colors[(QPalette.Disabled, QPalette.Text)],
               check='\n            image: url("{}");'.format(CHECK_IMAGE) if CHECK_IMAGE else "")


def register():
    """Add the brand themes to the themes module. Call before MainWindow is created (it builds the
    Theme menu from themes.themes and applies the theme in its constructor). Safe to call twice."""
    global _registered
    # KeRT Light is the only theme: drop upstream's themes (themes.py itself is left untouched so
    # that it does not conflict when merging upstream)
    brand_names = {name for name, _ in BRAND_THEMES}
    themes.themes[:] = [t for t in themes.themes if t[0] in brand_names]
    for name in list(themes.palettes):
        if name not in brand_names:
            del themes.palettes[name]
    for name, colors in BRAND_THEMES:
        if name in themes.palettes:
            continue
        palette = QPalette()
        for role, color in colors.items():
            if not hasattr(type(role), "__iter__"):
                role = [role]
            palette.setColor(*role, QColor(color))
        themes.palettes[name] = palette
        themes.themes.append((name, colors))

    if not _registered:
        # Theme.mask_light_factor() only knows upstream's "Light"; treat our light themes the same
        original = themes.Theme.mask_light_factor.__func__

        def mask_light_factor(cls):
            if cls.theme in LIGHT_THEME_NAMES:
                return 103
            return original(cls)

        themes.Theme.mask_light_factor = classmethod(mask_light_factor)

        # apply / clear our stylesheet whenever the theme changes
        original_set_theme = themes.Theme.set_theme.__func__

        def set_theme(cls, theme):
            original_set_theme(cls, theme)
            app = QApplication.instance()
            if app is not None:
                if theme in {n for n, _ in BRAND_THEMES}:
                    app.setStyle(BrandStyle(QStyleFactory.create("Fusion")))
                app.setStyleSheet(stylesheet(theme))

        themes.Theme.set_theme = classmethod(set_theme)
        _registered = True
