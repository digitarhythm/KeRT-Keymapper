# SPDX-License-Identifier: GPL-2.0-or-later
"""Branding theme (KeRT Color) and flat key rendering."""
import sys

import pytest
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, __import__("os").path.dirname(__file__))


UPSTREAM = ["Light", "Dark", "Arc", "Nord", "Olivia", "Dracula", "Bliss", "Catppuccin Latte",
            "Catppuccin Frappé", "Catppuccin Macchiato", "Catppuccin Mocha"]


def test_kert_color_registered(qtbot):
    import branding_theme
    import themes

    branding_theme.register()
    assert branding_theme.DEFAULT_THEME == "KeRT Color"
    assert "KeRT Color" in themes.palettes
    assert "KeRT Light" not in themes.palettes, "renamed to KeRT Color (2026-10-04)"
    # registering twice must not duplicate the menu entry
    branding_theme.register()
    assert [name for name, _ in themes.themes].count("KeRT Color") == 1

    # rebuilt as a copy of upstream's Arc (2026-10-04): every colour Arc sets, plus the outline colour
    # (Mid) the KeRT stylesheet draws its boxes with, which Arc leaves unset
    pal = themes.palettes["KeRT Color"]
    arc = dict(themes.themes)["Arc"]
    for role, colour in arc.items():
        args = role if isinstance(role, tuple) else (role,)
        assert pal.color(*args) == QColor(colour), role
    assert pal.color(QPalette.Mid) == QColor(branding_theme.KERT_OUTLINE)
    assert dict(branding_theme.BRAND_THEMES)["KeRT Color"][QPalette.Mid] == branding_theme.KERT_OUTLINE

    themes.Theme.set_theme("KeRT Color")
    try:
        assert themes.Theme.mask_light_factor() == 150, "a dark theme now, like Arc"
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_upstream_themes_are_back(qtbot):
    """ The Theme menu is back (2026-10-04): KeRT Color first, then upstream's themes """
    import branding_theme
    import themes

    branding_theme.register()
    assert [name for name, _ in themes.themes] == ["KeRT Color"] + UPSTREAM
    assert set(themes.palettes) == {"KeRT Color"} | set(UPSTREAM)


def test_theme_menu_visible(qtbot):
    """ The Theme menu shows System, KeRT Color and upstream's themes; KeRT Color is checked by default """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    assert mw.theme_menu.menuAction().isVisible()
    names = [a.data() for a in mw.theme_menu.actions()]
    assert names == ["System", "KeRT Color"] + UPSTREAM
    checked = [a.data() for a in mw.theme_menu.actions() if a.isChecked()]
    assert checked == [mw.get_theme()]


class FakeSettings:
    def __init__(self, values=None):
        self.values = dict(values or {})

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


def test_default_theme_resolution(qtbot):
    """ Nothing saved, an unknown name or the old "KeRT Color" give KeRT Color; a known theme is kept """
    import branding_theme

    branding_theme.register()
    for saved in (None, "", "Nope", "KeRT Light", "KeRT Color"):
        assert branding_theme.resolve_theme(saved) == "KeRT Color", saved
    for saved in ["System"] + UPSTREAM:
        assert branding_theme.resolve_theme(saved) == saved


def test_theme_saved_under_its_own_key(qtbot):
    """ The choice is kept under "kert_theme": a "theme" value left from before (when the menu was hidden
    and upstream names could be saved) is ignored """
    import branding_theme

    settings = FakeSettings({"theme": "Dark"})
    assert branding_theme.saved_theme(settings, web=False) == "KeRT Color"
    branding_theme.save_theme(settings, "Nord", web=False)
    assert settings.values["kert_theme"] == "Nord"
    assert branding_theme.saved_theme(settings, web=False) == "Nord"


def test_theme_saved_by_the_web_page(qtbot, monkeypatch):
    """ Browser build: Qt keeps QSettings in memory only, so the page stores the choice (localStorage) and
    hands it back as the KERT_THEME environment variable at the next start """
    import types
    import branding_theme

    sent = []
    monkeypatch.setitem(sys.modules, "vialglue", types.SimpleNamespace(save_theme=sent.append))
    monkeypatch.delenv("KERT_THEME", raising=False)
    settings = FakeSettings()
    assert branding_theme.saved_theme(settings, web=True) == "KeRT Color"
    monkeypatch.setenv("KERT_THEME", "Dracula")
    assert branding_theme.saved_theme(settings, web=True) == "Dracula"
    branding_theme.save_theme(settings, "Arc", web=True)
    assert sent == ["Arc"] and settings.values == {}


def test_upstream_theme_keeps_the_key_look(qtbot):
    """ Upstream themes (and System) get no KeRT boxes, but the black keys, tabs and see-through layer
    buttons stay: the keys are painted black whatever the theme """
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        for name in ("Dark", "System"):
            themes.Theme.set_theme(name)
            css = app.styleSheet()
            assert "3px solid #303030" not in css, name
            assert 'QPushButton[keyButton="true"]' in css and 'QPushButton[layerButton="true"]' in css, name
            assert "transparent" in css, name
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_widget_stylesheet(qtbot):
    """ KeRT Color rounds every box by 10px with a 3px line; other themes keep upstream's look """
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        themes.Theme.set_theme("KeRT Color")
        css = app.styleSheet()
        assert "border-radius: 10px" in css
        mid = dict(branding_theme.BRAND_THEMES)["KeRT Color"][QPalette.Mid]
        assert "3px solid " + mid in css
        assert "QPushButton" in css and "QTabBar::tab" in css and "EntryCard" in css
        # the keyboard selector gets twice the usual left padding in front of the keyboard name
        assert "QComboBox {" in css and "padding-left: 32px" in css.split("QComboBox {")[1].split("}")[0]
        # checkboxes (QMK Settings) are drawn dark, filled with the brand colour when checked
        assert "QCheckBox::indicator" in css and "2px solid " + mid in css
        hl = dict(branding_theme.BRAND_THEMES)["KeRT Color"][QPalette.Highlight]
        assert "QCheckBox::indicator:checked" in css and "background-color: " + hl in css.split("QCheckBox::indicator:checked")[1]
    finally:
        themes.Theme.set_theme("KeRT Color")




def test_highlight_keeps_dark_outline(qtbot):
    """ Selected tab / checked button / checked box: only the fill shows the highlight, the dark outline stays """
    import branding_theme
    theme = dict(branding_theme.BRAND_THEMES)["KeRT Color"]
    # selected tab / checked button / checked box keep the dark outline: only the fill turns grey
    import re
    import themes
    branding_theme.register()
    themes.Theme.set_theme("KeRT Color")
    css = QApplication.instance().styleSheet()
    for selector in ("QTabBar::tab:selected", "QPushButton:checked", "QCheckBox::indicator:checked"):
        block = re.search(re.escape(selector) + r"[^{]*\{([^}]*)\}", css).group(1)
        assert "background-color: " + theme[QPalette.Highlight] in block, selector
        assert "border-color: " + theme[QPalette.Highlight] not in block, selector

def test_selected_uses_background(qtbot):
    """ The selected tab and a checked (layer) button are filled with the brand colour, not just outlined """
    import re
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        themes.Theme.set_theme("KeRT Color")
        css = app.styleSheet()
        hl = dict(branding_theme.BRAND_THEMES)["KeRT Color"][QPalette.Highlight]
        for selector in ("QTabBar::tab:selected", "QPushButton:checked"):
            block = re.search(re.escape(selector) + r"[^{]*\{([^}]*)\}", css)
            assert block, selector
            assert "background-color: {}".format(hl) in block.group(1), selector
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_layout_spacing(qtbot):
    """ KeRT Color packs widgets with 3px margins and spacing, the same as its line width """
    from PyQt5.QtWidgets import QStyle
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    metrics = (QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutTopMargin, QStyle.PM_LayoutRightMargin,
               QStyle.PM_LayoutBottomMargin, QStyle.PM_LayoutHorizontalSpacing, QStyle.PM_LayoutVerticalSpacing)
    themes.Theme.set_theme("KeRT Color")
    assert all(app.style().pixelMetric(m) == 3 for m in metrics)


def test_flat_key_geometry(qtbot):
    from widgets.key_widget import KeyWidget
    import key_style

    assert key_style.FLAT_KEYS is True
    assert key_style.CORNER_RADIUS == 10
    assert key_style.OUTLINE_WIDTH == 3

    w = KeyWidget()
    key = w.widgets[0]
    assert key.corner == key_style.key_corner()      # 8 with the dark key look, CORNER_RADIUS without
    # no separate "top face": the key is one flat rounded rectangle
    assert key.foreground_draw_path.isEmpty()
    # the legend is centred on the whole key, not shifted up for a shadow
    assert key.text_rect == key.rect


def test_flat_key_paint(qtbot, monkeypatch):
    """ The previous white, outlined key look (key_style.DARK_KEYS = False); the dark look: test_dark_keys.py """
    import branding_theme
    import themes
    import key_style
    from widgets.key_widget import KeyWidget

    monkeypatch.setattr(key_style, "DARK_KEYS", False)

    branding_theme.register()
    themes.Theme.set_theme("KeRT Color")
    try:
        # a palette of its own with a light key on a lighter window and a dark outline: this tests the
        # outlined flat key's shape, and KeRT Color (Arc) has the same colour for keys and window
        from PyQt5.QtGui import QPalette as P
        pal = QApplication.palette()
        pal.setColor(P.Button, QColor("#ffffff"))
        pal.setColor(P.Window, QColor("#f5f6f8"))
        pal.setColor(P.Mid, QColor("#303030"))
        pal.setColor(P.ButtonText, QColor("#1f2328"))
        QApplication.setPalette(pal)
        w = KeyWidget()
        w.set_keycode("KC_A")
        qtbot.addWidget(w)
        w.resize(w.minimumSizeHint())
        img = w.grab().toImage()
        key = w.widgets[0]
        r = key.rect
        pal = QApplication.palette()

        # a point inside the key, away from the legend in the middle and from the outline
        inner = QColor(img.pixel(r.left() + r.width() // 4, r.top() + r.height() // 4))
        assert inner == pal.color(QPalette.Button)
        # a rounded corner: the very corner pixel of the key rect is the window background, not the key
        corner = QColor(img.pixel(r.left(), r.top()))
        assert corner != pal.color(QPalette.Button)
        # the outline: around the middle of the top edge there is a pixel darker than the key and the
        # background (the 1px antialiased line straddles the edge, so compare lightness, not exact colour)
        edge = min(QColor(img.pixel(r.center().x(), y)).lightness() for y in range(r.top() - 1, r.top() + 3))
        assert edge < pal.color(QPalette.Button).lightness() - 20
        assert edge < pal.color(QPalette.Window).lightness() - 20
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_selected_key_filled(qtbot, monkeypatch):
    """ White outlined look (DARK_KEYS = False): a selected key is filled with the highlight, keeps its
    outline, and its legend turns white. The dark look: test_dark_keys.py """
    import branding_theme
    import themes
    import key_style
    from widgets.key_widget import KeyWidget

    monkeypatch.setattr(key_style, "DARK_KEYS", False)

    branding_theme.register()
    themes.Theme.set_theme("KeRT Color")
    try:
        w = KeyWidget()
        w.set_keycode("KC_A")
        qtbot.addWidget(w)
        w.resize(w.minimumSizeHint())
        key = w.widgets[0]
        pal = QApplication.palette()
        r = key.rect
        inner = (r.left() + r.width() // 4, r.top() + r.height() // 4)

        # not selected: key colour
        assert QColor(w.grab().toImage().pixel(*inner)) == pal.color(QPalette.Button)

        # selected: brand colour, and somewhere in the legend area a HighlightedText pixel
        w.active_key = key
        img = w.grab().toImage()
        assert QColor(img.pixel(*inner)) == pal.color(QPalette.Highlight)
        hlt = pal.color(QPalette.HighlightedText)
        legend = [QColor(img.pixel(x, y)) for x in range(r.center().x() - 8, r.center().x() + 8)
                  for y in range(r.center().y() - 8, r.center().y() + 8)]
        assert any(c == hlt for c in legend), "legend of the selected key should use HighlightedText"
        # the dark outline stays on the selected key (a light grey fill without it reads as disabled)
        mid = pal.color(QPalette.Mid)
        edge = [QColor(img.pixel(r.center().x(), y)) for y in range(r.top(), r.top() + 6)]
        assert any(c == mid for c in edge), "selected key keeps the dark outline"
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_device_combobox_size(qtbot):
    """ The keyboard selector at the top is 1.4x as tall as a default combobox and uses a 4pt larger font """
    from PyQt5.QtWidgets import QComboBox
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    cb = mw.combobox_devices

    assert cb.font().pointSize() == QApplication.font().pointSize() + 4

    reference = QComboBox()
    qtbot.addWidget(reference)
    from main_window import HEADER_HEIGHT_FACTOR
    assert HEADER_HEIGHT_FACTOR == 1.4
    assert cb.height() >= round(HEADER_HEIGHT_FACTOR * reference.sizeHint().height())


def test_select_keyboard_icon(qtbot):
    """ A keyboard icon, as tall as the selector, sits immediately left of the keyboard selector """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    icon = mw.lbl_select_keyboard
    cb = mw.combobox_devices

    pm = icon.pixmap()
    assert pm is not None and not pm.isNull()
    assert pm.height() == cb.minimumHeight()
    # leftmost in the header row, followed by the logo image
    logo = mw.lbl_logo_image
    assert icon.mapToGlobal(icon.rect().topRight()).x() <= logo.mapToGlobal(logo.rect().topLeft()).x()


def test_no_text_logo(qtbot):
    """ The image logo replaced the "KeRT-Keymapper" text wordmark """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    assert not hasattr(mw, "lbl_logo")


def test_device_row_layout(qtbot):
    """ Selector as wide as its longest entry, square Refresh button right next to it, row left-aligned """
    from PyQt5.QtWidgets import QComboBox
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1700, 1000)   # room for the whole header row (logo image, label, selector, Refresh, wordmark)
    cb = mw.combobox_devices
    btn = mw.btn_refresh_devices
    qtbot.waitUntil(lambda: cb.width() >= cb.sizeHint().width())

    # width follows the longest keyboard name, not the window
    assert cb.sizeAdjustPolicy() == QComboBox.AdjustToContents
    assert cb.width() < mw.centralWidget().width() // 2

    # Refresh button: same font and height as the selector, wide enough for its text, immediately to its right
    assert btn.font().pointSize() == cb.font().pointSize()
    assert btn.height() == cb.height()
    assert btn.width() >= btn.fontMetrics().horizontalAdvance("Refresh")
    gap = btn.mapToGlobal(btn.rect().topLeft()).x() - cb.mapToGlobal(cb.rect().topRight()).x()
    assert 0 <= gap <= 6

    # right-aligned: Refresh ends near the right edge of the window (header margin only)
    assert mw.mapToGlobal(mw.rect().topRight()).x() - btn.mapToGlobal(btn.rect().topRight()).x() <= 12
    # ... while the logo stays at the left
    logo = mw.lbl_logo_image
    assert logo.mapToGlobal(logo.rect().topRight()).x() < cb.mapToGlobal(cb.rect().topLeft()).x() - 100

    # the selector is exactly as wide as its contents ask for (AdjustToContents), not stretched
    assert abs(cb.width() - cb.sizeHint().width()) <= 3


def test_picker_font_smaller(qtbot):
    """ Keycode picker buttons use a 2pt smaller font so that long Quantum labels fit; other buttons don't """
    from widgets.square_button import SquareButton
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    default_pt = QApplication.font().pointSize()

    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    quantum = [x for x in range(ak.count()) if ak.tabText(x) == "Quantum"][0]
    ak.setCurrentIndex(quantum)   # tabs build on first show
    buttons = ak.widget(quantum).findChildren(SquareButton)
    assert buttons
    assert all(b.font().pointSize() == default_pt - 2 for b in buttons)

    assert mw.keymap_editor.layer_buttons[0].font().pointSize() == default_pt


def test_header_margin(qtbot):
    """ The header row (keyboard selector) keeps a little inner margin, wider than the 3px used elsewhere """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    m = mw.layout_header.contentsMargins()
    assert (m.left(), m.top(), m.right(), m.bottom()) == (6, 6, 6, 6)


def test_picker_block_centered(qtbot):
    """ Picker tab contents are left-aligned inside a centred block; the block is capped at the available
    width (§4.5) and at least as wide as the display keyboard (2026-09-23: it used to be exactly that wide) """
    from widgets.square_button import SquareButton
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    # wide enough for the ANSI display keyboard alternative to be the one shown
    mw.resize(1700, 1800)   # portrait: the picker uses the full width (spec §4.5); wide enough for ansi_100
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    basic = ak.widget([x for x in range(ak.count()) if ak.tabText(x) == "Basic"][0])
    qtbot.waitUntil(lambda: any(a.isVisible() and a.kb_display is not None for a in basic.alternatives))
    alt = [a for a in basic.alternatives if a.isVisible() and a.kb_display is not None][0]
    qtbot.waitUntil(lambda: alt.block.width() > 0 and alt.kb_display.width() > 0)

    block, kb = alt.block, alt.kb_display
    gx = lambda w, p: w.mapToGlobal(p).x()
    # block: at least the display keyboard, at most the available width; the keyboard sits at its left
    assert kb.width() - 6 <= block.width() <= alt.available_width()
    assert abs(gx(kb, kb.rect().topLeft()) - gx(block, block.rect().topLeft())) <= 6
    # block is centred in the tab page (wait: the page re-centres the block on the layout pass after the
    # resize, which can come after the block got its width)
    qtbot.waitUntil(lambda: abs(gx(alt, alt.rect().center()) - gx(block, block.rect().center())) <= 6, timeout=3000)
    # contents are left-aligned inside the block
    assert abs(gx(kb, kb.rect().topLeft()) - gx(block, block.rect().topLeft())) <= 6
    first_item = alt.key_layout.itemAt(0).widget()   # the "Any" button comes first in the flow
    assert abs(gx(first_item, first_item.rect().topLeft()) - gx(block, block.rect().topLeft())) <= 6


def test_picker_key_size(qtbot):
    """ Picker keys are a little larger than upstream's: 3.4 font heights plus the outline """
    import key_style
    from constants import KEYCODE_BTN_RATIO
    from widgets.square_button import SquareButton
    from test_gui import prepare, FAKE_KEYBOARD

    assert KEYCODE_BTN_RATIO == 3.4
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    idx = [x for x in range(ak.count()) if ak.tabText(x) == "Quantum"][0]
    ak.setCurrentIndex(idx)   # tabs build on first show
    quantum = ak.widget(idx)
    btn = quantum.findChildren(SquareButton)[0]
    expected = round(btn.fontMetrics().height() * KEYCODE_BTN_RATIO) + 2 * key_style.OUTLINE_WIDTH
    assert btn.sizeHint().height() == expected


def test_logo_image(qtbot):
    """ The KeRT-Keymapper logo image sits at the left of the header, scaled to the selector's height """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    img = mw.lbl_logo_image
    cb = mw.combobox_devices
    icon = mw.lbl_select_keyboard

    pm = img.pixmap()
    assert pm is not None and not pm.isNull()
    assert pm.height() == cb.minimumHeight()
    assert 4 <= pm.width() / pm.height() <= 6          # 1600x320 source keeps its aspect ratio
    # between the keyboard icon and the selector
    assert icon.mapToGlobal(icon.rect().topRight()).x() <= img.mapToGlobal(img.rect().topLeft()).x()
    assert img.mapToGlobal(img.rect().topRight()).x() <= cb.mapToGlobal(cb.rect().topLeft()).x()



def test_header_images_black_base(qtbot):
    """ The header keyboard icon follows the black logo (2026-09-27): a black body with the logo's grey
    (#888888) rim and no KeRT green left; the app ships the current originals from misc/ """
    import os
    from collections import Counter
    from PyQt5.QtGui import QImage

    root = os.path.join(os.path.dirname(__file__), "../../../..")
    res = os.path.join(root, "src/main/resources/base")
    for name in ("keyboard-icon.png", "kert-keymapper.png"):
        with open(os.path.join(root, "misc", name), "rb") as a, open(os.path.join(res, name), "rb") as b:
            assert a.read() == b.read(), name + ": the shipped copy is not the misc/ original"

    img = QImage(os.path.join(res, "keyboard-icon.png"))
    assert not img.isNull()
    opaque = Counter()
    for y in range(0, img.height(), 2):
        for x in range(0, img.width(), 2):
            c = QColor.fromRgba(img.pixel(x, y))
            if c.alpha() == 255:
                opaque[c.name()] += 1
    # only greys: black and the logo's rim colour, nothing green
    assert all(abs(QColor(n).red() - QColor(n).green()) <= 2 and abs(QColor(n).green() - QColor(n).blue()) <= 2
               for n in opaque), "no coloured pixels"
    assert opaque.most_common(1)[0][0] == "#000000"
    assert opaque["#888888"] > 0

def test_picker_block_full_width_without_keyboard(qtbot):
    """ Tabs without a display keyboard (Layers, Tap Dance, ...) use the whole width and wrap horizontally """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(900, 1200)   # portrait: full width (a landscape window wraps at its height, spec §4.5)
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    idx = [x for x in range(ak.count()) if ak.tabText(x) == "Layers"][0]
    ak.setCurrentIndex(idx)
    layers = ak.widget(idx)
    qtbot.waitUntil(lambda: any(a.isVisible() for a in layers.alternatives))
    alt = [a for a in layers.alternatives if a.isVisible()][0]
    assert alt.kb_display is None
    qtbot.waitUntil(lambda: alt.block.width() > 0)

    # the block spans the page, so the flow can lay buttons out side by side
    assert alt.block.width() >= alt.width() - 6
    items = [alt.key_layout.itemAt(i).widget() for i in range(min(3, alt.key_layout.count()))]
    assert len(items) >= 2
    assert items[0].y() == items[1].y(), "buttons must wrap horizontally, not stack in one column"


def test_picker_block_centered_without_keyboard(qtbot):
    """ A tab whose buttons fit in one row (User) gets a content-wide, centred, left-aligned block """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1700, 1800)   # portrait: the picker uses the full width (spec §4.5); wide enough for ansi_100
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    idx = [x for x in range(ak.count()) if ak.tabText(x) == "User"][0]
    ak.setCurrentIndex(idx)
    page = ak.widget(idx)
    qtbot.waitUntil(lambda: any(a.isVisible() for a in page.alternatives))
    alt = [a for a in page.alternatives if a.isVisible()][0]
    gx = lambda w, p: w.mapToGlobal(p).x()
    qtbot.waitUntil(lambda: 0 < alt.block.width() < alt.width() - 100
                    and abs(gx(alt, alt.rect().center()) - gx(alt.block, alt.block.rect().center())) <= 6)
    first = alt.key_layout.itemAt(0).widget()
    assert abs(gx(first, first.rect().topLeft()) - gx(alt.block, alt.block.rect().topLeft())) <= 6
    items = [alt.key_layout.itemAt(i).widget() for i in range(alt.key_layout.count())]
    assert len({w.y() for w in items}) == 1, "all User buttons fit in a single row"


def test_checkbox_check_mark(qtbot):
    """ A checked checkbox shows a white check mark on top of its brand-colour background """
    import os
    from PyQt5.QtWidgets import QCheckBox, QStyle, QStyleOptionButton
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    css = QApplication.instance().styleSheet()
    checked_rule = css.split("QCheckBox::indicator:checked")[1].split("}")[0]
    assert 'image: url("' in checked_rule
    path = checked_rule.split('url("')[1].split('"')[0]
    assert path.endswith("check.svg") and os.path.exists(path)

    hl = QApplication.palette().color(QPalette.Highlight)

    def white_pixels(checked):
        """(pixels of the highlight colour, pixels clearly darker than it - the mark), indicator rect"""
        box = QCheckBox("x", mw)
        box.setChecked(checked)
        box.resize(box.sizeHint())
        box.show()
        qtbot.waitExposed(box)
        opt = QStyleOptionButton()
        box.initStyleOption(opt)
        ind = box.style().subElementRect(QStyle.SE_CheckBoxIndicator, opt, box)
        image = box.grab().toImage()
        inner = ind.adjusted(4, 4, -4, -4)
        pixels = [QColor(image.pixel(x, y)) for x in range(inner.left(), inner.right() + 1)
                  for y in range(inner.top(), inner.bottom() + 1)]
        filled = sum(1 for c in pixels if c == hl)
        mark = sum(1 for c in pixels if c.lightness() < hl.lightness() - 60)
        box.hide()
        return (filled, mark), ind

    (filled, mark), ind = white_pixels(True)
    (filled_off, _), _ = white_pixels(False)
    assert ind.width() >= 18
    # checked: the highlight colour with the (dark) check mark on it; unchecked: no highlight colour
    assert filled > 0 and mark > 0
    assert filled_off == 0


def test_editor_tabs_centred(qtbot):
    """ The editor tab bar (Keymap, Macros, ...) is centred above the editors """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1600, 1000)
    mw.set_mode("definitions")             # the main tab bar shows in Definitions mode
    bar = mw.tabs.tabBar()
    qtbot.waitUntil(lambda: bar.width() > 0 and mw.tabs.width() >= 1500)
    assert mw.tabs.objectName() == "editor_tabs"
    assert "alignment: center" in QApplication.instance().styleSheet()
    bar_centre = bar.mapTo(mw.tabs, bar.rect().center()).x()
    assert abs(bar_centre - mw.tabs.width() / 2) < mw.tabs.width() * 0.05

    # the keycode picker's tab bar (Basic, ISO/JIS, ...) is centred too
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    assert ak.objectName() == "picker_tabs"
    pbar = ak.tabBar()
    qtbot.waitUntil(lambda: pbar.width() > 0 and ak.width() > 1000)
    pbar_centre = pbar.mapTo(ak, pbar.rect().center()).x()
    assert abs(pbar_centre - ak.width() / 2) < ak.width() * 0.05


def test_inner_editor_tabs_centred(qtbot):
    """ The tab bars inside the Macros, Key Override, Alt Repeat Key and QMK Settings editors are centred too """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1600, 1000)
    mw.set_mode("definitions")             # the main tab bar shows in Definitions mode
    assert "QTabWidget::tab-bar {" in QApplication.instance().styleSheet()
    checked = 0
    for editor, label in ((mw.macro_recorder, "Macros"), (mw.key_override, "Key Overrides"),
                          (mw.alt_repeat_key, "Alt Repeat Key"), (mw.qmk_settings, "QMK Settings")):
        tabs = getattr(editor, "tabs", None) or getattr(editor, "tabs_widget", None)
        if not editor.valid() or label not in mw._tab_labels or tabs.count() == 0:
            continue
        mw.tabs.setCurrentIndex(mw._tab_labels.index(label))    # show it so the bar gets laid out
        bar = tabs.tabBar()
        qtbot.waitUntil(lambda: bar.isVisible() and bar.width() > 0 and tabs.width() > 500)
        bar_centre = bar.mapTo(tabs, bar.rect().center()).x()
        assert abs(bar_centre - tabs.width() / 2) < tabs.width() * 0.05, label
        checked += 1
    assert checked >= 1     # the virtual test keyboard only has Macros of these


def test_tabs_centred_in_every_theme(qtbot):
    """ The tab bars are centred whatever the theme (2026-10-04: upstream themes and System too) """
    import re
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        for name in ("KeRT Color", "Dark", "Nord", "System"):
            themes.Theme.set_theme(name)
            block = re.search(r"QTabWidget::tab-bar\s*\{([^}]*)\}", app.styleSheet())
            assert block and "alignment: center" in block.group(1), name
    finally:
        themes.Theme.set_theme("KeRT Color")
