# SPDX-License-Identifier: GPL-2.0-or-later
"""Two large mode buttons right of the header logo (2026-10-10, docs/mode-buttons-spec.md):
- "Key mapping": the Keymap editor alone, no tab bar;
- "Definitions": the other editors' tabs (no Keymap tab), Macros selected by default.
Keymap no longer sits in one row with the definition tabs, so the two modes do not mix."""
import os
import sys
import xml.etree.ElementTree as ET

from PyQt5.QtCore import Qt

sys.path.insert(0, os.path.dirname(__file__))


def window(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, combos=[[0, 0, 0, 0, 0]], tap_dance=[[0, 0, 0, 0, 200]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw


def labels(mw):
    return [mw.tabs.tabText(i) for i in range(mw.tabs.count())]


def test_buttons_right_of_the_logo(qtbot):
    from PyQt5.QtWidgets import QPushButton
    mw = window(qtbot)
    km, df = mw.btn_mode_keymap, mw.btn_mode_definitions
    assert isinstance(km, QPushButton) and isinstance(df, QPushButton)
    assert km.text() == "Key mapping" and df.text() == "Definitions"
    logo = mw.lbl_logo_image
    gx = lambda w: w.mapToGlobal(w.rect().topLeft()).x()
    assert gx(logo) + logo.width() <= gx(km) < gx(df), "right of the logo, Key mapping first"
    assert gx(df) + df.width() < gx(mw.combobox_devices), "left of the keyboard selector"
    # large: as tall as the keyboard selector, a font a little larger than the default and a little smaller
    # than the selector's (2026-10-10), both buttons as wide as each other
    # a little slimmer than the keyboard selector (2026-10-10), still taller than their text
    sel = mw.combobox_devices.minimumHeight()
    assert km.height() == df.height() and int(sel * 0.7) <= km.height() <= int(sel * 0.85)
    assert km.height() > km.fontMetrics().height() + 6
    assert mw.font().pointSizeF() < km.font().pointSizeF() < mw.combobox_devices.font().pointSizeF()
    assert df.font().pointSizeF() == km.font().pointSizeF()
    assert km.width() == df.width()
    # more room left and right of the text (2026-10-10): each side at least MODE_SIDE_MARGIN more than the
    # style's own padding
    import main_window
    assert main_window.MODE_SIDE_MARGIN >= 10
    for b in (km, df):
        text = b.fontMetrics().horizontalAdvance(b.text())
        assert b.width() - text >= 2 * main_window.MODE_SIDE_MARGIN + 16, (b.text(), b.width(), text)
    assert km.isCheckable() and df.isCheckable()


def test_starts_in_key_mapping_mode(qtbot):
    mw = window(qtbot)
    assert mw.mode == "keymap"
    assert mw.btn_mode_keymap.isChecked() and not mw.btn_mode_definitions.isChecked()
    assert labels(mw) == ["Keymap"]
    assert not mw.tabs.tabBar().isVisible(), "no tab bar in this mode"
    assert mw.tabs.currentWidget().editor is mw.keymap_editor


def test_definitions_show_the_other_tabs_macros_first(qtbot):
    mw = window(qtbot)
    qtbot.mouseClick(mw.btn_mode_definitions, Qt.LeftButton)
    assert mw.mode == "definitions"
    assert mw.btn_mode_definitions.isChecked() and not mw.btn_mode_keymap.isChecked()
    shown = labels(mw)
    assert "Keymap" not in shown
    assert shown == [lbl for c, lbl in mw.editors if c.valid() and lbl != "Keymap"]
    assert {"Macros", "Tap Dance", "Combos"} <= set(shown)
    # the order (2026-10-10): Tap Dance, HostOS, Combos, Macros, Key Overrides, Alt Repeat Key, QMK Settings,
    # Matrix tester, then the ones only some keyboards have
    order = [lbl for c, lbl in mw.editors if lbl != "Keymap"]
    assert order[:8] == ["Tap Dance", "HostOS", "Combos", "Macros", "Key Overrides", "Alt Repeat Key",
                         "QMK Settings", "Matrix tester"]
    assert mw.tabs.tabText(mw.tabs.currentIndex()) == "Tap Dance", "Tap Dance selected by default (2026-10-10)"
    assert mw.tabs.tabBar().isVisible()
    # back to Key mapping
    qtbot.mouseClick(mw.btn_mode_keymap, Qt.LeftButton)
    assert labels(mw) == ["Keymap"] and not mw.tabs.tabBar().isVisible()
    assert mw.tabs.currentWidget().editor is mw.keymap_editor


def test_definitions_open_on_tap_dance_each_time(qtbot):
    mw = window(qtbot)
    mw.set_mode("definitions")
    mw.tabs.setCurrentIndex(labels(mw).index("Combos"))
    mw.set_mode("keymap")
    mw.set_mode("definitions")
    assert mw.tabs.tabText(mw.tabs.currentIndex()) == "Tap Dance"


def test_checked_mode_button_shows_in_every_theme(qtbot):
    """the checked mode button is filled with the theme's highlight (and its text colour), in any theme -
    KeRT Color's stylesheet does it for every checked button, the others get a rule of their own (2026-10-10)"""
    import re
    import branding_theme
    import themes
    from PyQt5.QtGui import QColor, QPalette
    from PyQt5.QtWidgets import QApplication
    mw = window(qtbot)
    assert mw.btn_mode_keymap.property("modeButton") and mw.btn_mode_definitions.property("modeButton")
    try:
        for name in ("Dark", "Light", "Nord", "KeRT Color"):
            themes.Theme.set_theme(name)
            css = QApplication.instance().styleSheet()
            rule = re.search(r'QPushButton\[modeButton="true"\]:checked\s*\{([^}]*)\}', css)
            if name == "KeRT Color":
                assert rule is None, "KeRT Color keeps its own look for checked buttons"
                assert re.search(r"QPushButton:checked[^{]*\{[^}]*background-color", css)
                continue
            assert rule and "palette(highlight)" in rule.group(1) and "palette(highlighted-text)" in rule.group(1), name
            btn = mw.btn_mode_keymap
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            img = btn.grab().toImage()
            c = QColor(img.pixel(6, btn.height() // 2))       # just inside the left edge, clear of the text
            hl = QApplication.palette().color(QPalette.Highlight)
            assert abs(c.red() - hl.red()) + abs(c.green() - hl.green()) + abs(c.blue() - hl.blue()) <= 30, \
                (name, c.name(), hl.name())
    finally:
        themes.Theme.set_theme("KeRT Color")


def test_editors_kept_between_modes(qtbot):
    """switching modes reuses the editors' containers (no rebuild: it is slow in the browser)"""
    mw = window(qtbot)
    keymap_page = mw.tabs.widget(0)
    mw.set_mode("definitions")
    macros_page = mw.tabs.currentWidget()
    mw.set_mode("keymap")
    assert mw.tabs.widget(0) is keymap_page
    mw.set_mode("definitions")
    assert mw.tabs.currentWidget() is macros_page


def test_mode_buttons_translated():
    path = os.path.join(os.path.dirname(__file__), "../../resources/base/translations/kert_ja.ts")
    root = ET.parse(path).getroot()
    found = {m.find("source").text: m.find("translation").text
             for ctx in root.findall("context") if ctx.find("name").text == "MainWindow"
             for m in ctx.findall("message")}
    assert found.get("Key mapping") == "キーマッピング"
    assert found.get("Definitions") == "各種定義"
    # the Definitions tabs (2026-10-10)
    for en, ja in (("Tap Dance", "タップダンス"), ("HostOS", "ホストOS"), ("Combos", "コンボ"), ("Macros", "マクロ"),
                   ("Key Overrides", "キー上書き"), ("Alt Repeat Key", "代替キー"), ("QMK Settings", "QMK設定"),
                   ("Matrix tester", "キーテスター")):
        assert found.get(en) == ja, en
