# SPDX-License-Identifier: GPL-2.0-or-later
"""This fork's own themes, registered without editing upstream's themes.py
(see docs/rebranding-plan.md section 6 and docs/theme-flat-keys-spec.md)."""

import os
import sys

from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication, QProxyStyle, QStyle, QStyleFactory

import key_style
import themes

# the default theme and first in the Theme menu (2026-10-04: "KeRT Light" renamed, the menu is back with
# upstream's themes after it; docs/theme-menu-spec.md)
DEFAULT_THEME = "KeRT Color"
# saved under its own key: "theme" may still hold an upstream name saved while the menu was hidden
SETTINGS_KEY = "kert_theme"

# light themes: the inner part of a masked key is drawn only slightly lighter than the key (none of ours
# since KeRT Color became a copy of the dark Arc)
LIGHT_THEME_NAMES = set()

# outline colour of the boxes the KeRT stylesheet draws (QPalette.Mid, which Arc leaves unset): Arc's own
# border shade, a little darker than its window
KERT_OUTLINE = "#2b2e39"

# KeRT Color: a copy of upstream's Arc palette (themes.py; 2026-10-04, light grey #f5f6f8 with #f0f0f0
# selection before), plus the outline colour
_KERT_COLOR = dict(dict(themes.themes)["Arc"])
_KERT_COLOR[QPalette.Mid] = KERT_OUTLINE
BRAND_THEMES = [
    (DEFAULT_THEME, _KERT_COLOR),
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
    """A saved theme name that the Theme menu offers ("System" or a registered theme) is kept; nothing,
    an unknown name or the old "KeRT Light" give DEFAULT_THEME"""
    if saved == "System" or saved in {name for name, _ in themes.themes}:
        return saved
    return DEFAULT_THEME


def saved_theme(settings, web=None):
    """The theme chosen last time: QSettings on the desktop, the page's localStorage (handed over as the
    KERT_THEME environment variable) in the browser, where Qt keeps QSettings in memory only"""
    if web is None:
        web = sys.platform == "emscripten"
    saved = os.environ.get("KERT_THEME") if web else settings.value(SETTINGS_KEY, None)
    return resolve_theme(saved)


def save_theme(settings, name, web=None):
    if web is None:
        web = sys.platform == "emscripten"
    if web:
        import vialglue
        vialglue.save_theme(name)
    else:
        settings.setValue(SETTINGS_KEY, name)


# rules for every theme (upstream's and System too, 2026-10-04)
COMMON_STYLE = """
        QTabWidget::tab-bar {
            alignment: center;   /* every tab bar: editors, picker, and the tabs inside Macros / Key Override / Alt Repeat Key / QMK Settings */
        }
"""


def stylesheet(name):
    """Application stylesheet for one of our themes: every box gets the same rounded corners and
    line width as the keys. Other themes (upstream's, "System") keep their own look except for the dark
    key look (key_button_style), as the keys are painted black whatever the theme."""
    if name not in {n for n, _ in BRAND_THEMES}:
        pal = QApplication.palette()
        return COMMON_STYLE + key_button_style({QPalette.Highlight: pal.color(QPalette.Highlight).name(),
                                                QPalette.HighlightedText: pal.color(QPalette.HighlightedText).name()})
    colors = dict(BRAND_THEMES)[name]
    mid = colors[QPalette.Mid]
    r = key_style.CORNER_RADIUS
    w = key_style.OUTLINE_WIDTH
    return ("""
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
        /* highlighted: light grey fill, the dark outline stays (a grey box without it reads as disabled) */
        QPushButton:pressed, QToolButton:pressed, EntryCardButton:pressed,
        QPushButton:checked, QToolButton:checked {{
            background-color: {hl};
            color: {hlt};
        }}
        /* layer buttons are see-through: the highlight behind them (widgets/layer_highlight.py) slides
           to the chosen layer; the button over it gets white text through the "lit" property */
        QPushButton[layerButton="true"], QPushButton[layerButton="true"]:checked,
        QPushButton[layerButton="true"]:pressed, QPushButton[layerButton="true"]:disabled {{
            background-color: transparent;
            color: {text};
        }}
        QPushButton[layerButton="true"][lit="true"] {{
            color: {hlt};
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
            background-color: {hl};{check}
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
               text=colors[QPalette.ButtonText],
               check='\n            image: url("{}");'.format(CHECK_IMAGE) if CHECK_IMAGE else "")
            + COMMON_STYLE + key_button_style(colors))


def key_button_style(colors):
    """The dark key look (key_style.DARK_KEYS) for picker key buttons, tabs and layer buttons: black
    face, white legend, no outline, KEY_RADIUS corners. Picker keys and tabs keep KEY_MARGINS free for
    the shadow painted under them (SquareButton.paintEvent, widgets/key_shadow.py); the layer buttons'
    faces and shadows are painted by widgets/layer_highlight.py. These rules come last and win."""
    if not key_style.DARK_KEYS:
        return ""
    return """
        QPushButton[keyButton="true"] {{
            background-color: {face};
            color: {legend};
            border: none;
            border-radius: {r}px;
            margin: {mt}px {mr}px {mb}px {ml}px;
            padding: 0px;
        }}
        QPushButton[keyButton="true"]:pressed {{
            background-color: {hl};
            color: {hlt};
        }}
        QPushButton[keyButton="true"] QLabel {{
            color: {legend};
        }}
        QTabBar::tab {{
            background-color: {face};
            color: {legend};
            border: none;
            border-radius: {r}px;
            margin: {mt}px {mr}px {mb}px {ml}px;
            padding: 4px 12px;
        }}
        QTabBar::tab:hover {{
            background-color: {hover};
        }}
        QTabBar::tab:selected {{
            background-color: {hl};
            color: {hlt};
        }}
        DeviceComboBox {{
            background-color: {face};
            color: {legend};
            border: none;
            border-radius: {r}px;
            margin: {mt}px {mr}px {mb}px {ml}px;
        }}
        DeviceComboBox:hover {{
            background-color: {hover};
        }}
        QPushButton[layerButton="true"], QPushButton[layerButton="true"]:checked,
        QPushButton[layerButton="true"]:pressed, QPushButton[layerButton="true"]:disabled {{
            background-color: transparent;
            color: {legend};
            border: none;
            border-radius: {r}px;
        }}
        /* the label the highlight box covers: dark on the light box. Listed last, and with :disabled too,
           because the current layer's button is disabled and the rule above would otherwise win */
        QPushButton[layerButton="true"][lit="true"], QPushButton[layerButton="true"][lit="true"]:disabled {{
            color: {hlt};
        }}
    """.format(face=key_style.face_css(), legend=key_style.KEY_LEGEND, r=key_style.KEY_RADIUS,
               hover=key_style.face_css(key_style.KEY_HOVER_FACE), hl=colors[QPalette.Highlight], hlt=colors[QPalette.HighlightedText],
               ml=key_style.KEY_MARGINS[0], mt=key_style.KEY_MARGINS[1], mr=key_style.KEY_MARGINS[2],
               mb=key_style.KEY_MARGINS[3])


def register():
    """Add the brand themes to the themes module. Call before MainWindow is created (it builds the
    Theme menu from themes.themes and applies the theme in its constructor). Safe to call twice."""
    global _registered
    # our themes first in the Theme menu, upstream's after them (themes.py itself is left untouched so
    # that it does not conflict when merging upstream)
    brand_names = {name for name, _ in BRAND_THEMES}
    themes.themes[:] = list(BRAND_THEMES) + [t for t in themes.themes if t[0] not in brand_names]
    for name, colors in BRAND_THEMES:
        if name in themes.palettes:
            continue
        palette = QPalette()
        for role, color in colors.items():
            if not hasattr(type(role), "__iter__"):
                role = [role]
            palette.setColor(*role, QColor(color))
        themes.palettes[name] = palette

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
