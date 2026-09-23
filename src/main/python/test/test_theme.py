# SPDX-License-Identifier: GPL-2.0-or-later
"""Branding theme (KeRT Light) and flat key rendering."""
import sys

import pytest
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, __import__("os").path.dirname(__file__))


def test_kert_light_registered(qtbot):
    import branding_theme
    import themes

    branding_theme.register()
    assert "KeRT Light" in themes.palettes
    assert "KeRT Light" in [name for name, _ in themes.themes]
    # registering twice must not duplicate the menu entry
    branding_theme.register()
    assert [name for name, _ in themes.themes].count("KeRT Light") == 1

    pal = themes.palettes["KeRT Light"]
    assert pal.color(QPalette.Window).lightness() > 230
    assert pal.color(QPalette.Mid) == QColor("#303030")        # dark outlines and borders
    assert pal.color(QPalette.Button) == QColor("#ffffff")
    assert pal.color(QPalette.ButtonText).lightness() < 80

    themes.Theme.set_theme("KeRT Light")
    try:
        assert themes.Theme.mask_light_factor() == 103
    finally:
        themes.Theme.set_theme("KeRT Light")


def test_only_kert_light(qtbot):
    """ KeRT Light is the one and only theme: nothing else is registered and there is no Theme menu """
    import branding_theme
    import themes
    from test_gui import prepare, FAKE_KEYBOARD

    branding_theme.register()
    assert [name for name, _ in themes.themes] == ["KeRT Light"]
    assert set(themes.palettes) == {"KeRT Light"}

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    assert not mw.theme_menu.menuAction().isVisible()
    assert mw.get_theme() == "KeRT Light"


def test_default_theme_resolution(qtbot):
    """ A saved upstream theme name (from before the rebranding) falls back to KeRT Light """
    import branding_theme

    for saved in (None, "Dark", "Bliss", "System", "KeRT Light"):
        assert branding_theme.resolve_theme(saved) == "KeRT Light"


def test_widget_stylesheet(qtbot):
    """ KeRT Light rounds every box by 10px with a 3px line; other themes keep upstream's look """
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        themes.Theme.set_theme("KeRT Light")
        css = app.styleSheet()
        assert "border-radius: 10px" in css
        assert "3px solid #303030" in css
        assert "QPushButton" in css and "QTabBar::tab" in css and "EntryCard" in css
        # the keyboard selector gets twice the usual left padding in front of the keyboard name
        assert "QComboBox {" in css and "padding-left: 32px" in css.split("QComboBox {")[1].split("}")[0]
        # checkboxes (QMK Settings) are drawn dark, filled with the brand colour when checked
        assert "QCheckBox::indicator" in css and "2px solid #303030" in css
        assert "QCheckBox::indicator:checked" in css and "background-color: #00a3a3" in css.split("QCheckBox::indicator:checked")[1]
    finally:
        themes.Theme.set_theme("KeRT Light")


def test_selected_uses_background(qtbot):
    """ The selected tab and a checked (layer) button are filled with the brand colour, not just outlined """
    import re
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    try:
        themes.Theme.set_theme("KeRT Light")
        css = app.styleSheet()
        hl = dict(branding_theme.BRAND_THEMES)["KeRT Light"][QPalette.Highlight]
        for selector in ("QTabBar::tab:selected", "QPushButton:checked"):
            block = re.search(re.escape(selector) + r"[^{]*\{([^}]*)\}", css)
            assert block, selector
            assert "background-color: {}".format(hl) in block.group(1), selector
    finally:
        themes.Theme.set_theme("KeRT Light")


def test_layout_spacing(qtbot):
    """ KeRT Light packs widgets with 3px margins and spacing, the same as its line width """
    from PyQt5.QtWidgets import QStyle
    import branding_theme
    import themes

    branding_theme.register()
    app = QApplication.instance()
    metrics = (QStyle.PM_LayoutLeftMargin, QStyle.PM_LayoutTopMargin, QStyle.PM_LayoutRightMargin,
               QStyle.PM_LayoutBottomMargin, QStyle.PM_LayoutHorizontalSpacing, QStyle.PM_LayoutVerticalSpacing)
    themes.Theme.set_theme("KeRT Light")
    assert all(app.style().pixelMetric(m) == 3 for m in metrics)


def test_flat_key_geometry(qtbot):
    from widgets.key_widget import KeyWidget
    import key_style

    assert key_style.FLAT_KEYS is True
    assert key_style.CORNER_RADIUS == 10
    assert key_style.OUTLINE_WIDTH == 3

    w = KeyWidget()
    key = w.widgets[0]
    assert key.corner == key_style.CORNER_RADIUS
    # no separate "top face": the key is one flat rounded rectangle
    assert key.foreground_draw_path.isEmpty()
    # the legend is centred on the whole key, not shifted up for a shadow
    assert key.text_rect == key.rect


def test_flat_key_paint(qtbot):
    import branding_theme
    import themes
    from widgets.key_widget import KeyWidget

    branding_theme.register()
    themes.Theme.set_theme("KeRT Light")
    try:
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
        themes.Theme.set_theme("KeRT Light")


def test_selected_key_filled(qtbot):
    """ A selected key is filled with the brand colour (not only outlined) and its legend turns white """
    import branding_theme
    import themes
    from widgets.key_widget import KeyWidget

    branding_theme.register()
    themes.Theme.set_theme("KeRT Light")
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
    finally:
        themes.Theme.set_theme("KeRT Light")


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
    # block is centred in the tab page
    page_centre = gx(alt, alt.rect().center())
    block_centre = gx(block, block.rect().center())
    assert abs(page_centre - block_centre) <= 6
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

    def white_pixels(checked):
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
        n = sum(1 for x in range(inner.left(), inner.right() + 1) for y in range(inner.top(), inner.bottom() + 1)
                if QColor(image.pixel(x, y)).lightness() > 200)
        box.hide()
        return n, ind

    n_checked, ind = white_pixels(True)
    n_unchecked, _ = white_pixels(False)
    assert ind.width() >= 18
    assert n_checked > 0
    # unchecked: white background everywhere, checked: mostly brand colour with a white mark
    assert n_checked < n_unchecked


def test_editor_tabs_centred(qtbot):
    """ The editor tab bar (Keymap, Macros, ...) is centred above the editors """
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1600, 1000)
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
