# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap tab: 30:70 split between keyboard and picker, keyboard auto-fitted to the top pane
(docs/theme-flat-keys-spec.md §4.4)."""
import os
import sys

from pytestqt.qt_compat import qt_api

sys.path.insert(0, os.path.dirname(__file__))


def prepared(qtbot, width=1400, height=1000):
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(width, height)
    ke = mw.keymap_editor
    qtbot.waitUntil(lambda: abs(ke.splitter.height() - sum(ke.splitter.sizes()) - ke.splitter.handleWidth()) <= 1)
    return mw, ke


def test_top_bottom_split(qtbot):
    from editor.keymap_editor import RatioSplitter, SPLIT_RATIO

    mw, ke = prepared(qtbot)
    assert isinstance(ke.splitter, RatioSplitter) and SPLIT_RATIO == (3, 7)
    top, bottom = ke.splitter.sizes()
    assert ke.splitter.widget(0) is ke.keyboard_area and ke.splitter.widget(1) is ke.tabbed_keycodes
    # only one picker (the unfiltered one) is visible; the masked-key picker stays hidden until needed
    assert ke.tabbed_keycodes.all_keycodes.isVisible() and ke.tabbed_keycodes.basic_keycodes.isHidden()
    assert abs(top / (top + bottom) - 0.3) < 0.02

    # the ratio survives a window resize
    mw.resize(1600, 1200)
    qtbot.waitUntil(lambda: ke.splitter.height() >= 1000)
    top, bottom = ke.splitter.sizes()
    assert abs(top / (top + bottom) - 0.3) < 0.02


def test_keyboard_auto_fit(qtbot):
    from editor.keymap_editor import MAX_FIT_SCALE

    mw, ke = prepared(qtbot)
    kb = ke.container
    space_w, space_h = ke.keyboard_space()
    assert kb.fit_mode and ke.auto_fit
    assert abs(kb.scale - kb.fit_scale(space_w, space_h, max_scale=MAX_FIT_SCALE)) < 0.001
    assert kb.width <= space_w + 1 and kb.height <= space_h + 1
    # the largest scale that fits: either a dimension is (almost) filled or the cap is hit
    filled = kb.width >= space_w - 2 * kb.padding - 2 or kb.height >= space_h - 2 * kb.padding - 2
    assert filled or abs(kb.scale - MAX_FIT_SCALE) < 0.001

    # a smaller window gives a smaller keyboard, still fitting the top pane
    before = kb.scale
    mw.resize(700, 500)
    qtbot.waitUntil(lambda: kb.scale < before)
    space_w, space_h = ke.keyboard_space()
    assert kb.width <= space_w + 1 and kb.height <= space_h + 1


def test_manual_zoom_stops_auto_fit(qtbot):
    from PyQt5.QtWidgets import QPushButton

    mw, ke = prepared(qtbot)
    kb = ke.container
    btn_plus = ke.layout_size.itemAt(0).widget()
    assert QPushButton.text(btn_plus) == "+"
    fitted = kb.scale
    qtbot.mouseClick(btn_plus, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert kb.scale > fitted and not ke.auto_fit and not kb.fit_mode

    # resizing no longer rescales the keyboard
    mw.resize(1600, 1200)
    qtbot.waitUntil(lambda: ke.splitter.height() >= 1000)
    assert abs(kb.scale - (fitted + 0.1)) < 0.001



def visible_alternative(tab):
    return [a for a in tab.alternatives if a.isVisible()][0]


def picker_tab(ak, label):
    idx = [x for x in range(ak.count()) if ak.tabText(x) == label][0]
    ak.setCurrentIndex(idx)
    return ak.widget(idx)


def landscape(qtbot, width=1600, height=900):
    mw, ke = prepared(qtbot, width, height)
    qtbot.waitUntil(lambda: mw.width() >= width - 50 and mw.height() < mw.width())
    return mw, ke


def test_picker_wraps_in_landscape(qtbot):
    mw, ke = landscape(qtbot)
    wrap = mw.height()
    assert ke.tabbed_keycodes.wrap_width == wrap
    ak = ke.tabbed_keycodes.all_keycodes
    assert ak.width() > wrap + 50, "the picker must be wider than the wrap width for the test to mean anything"

    layers = picker_tab(ak, "Layers")
    alt = visible_alternative(layers)
    qtbot.waitUntil(lambda: alt.block.width() > 0)
    assert alt.block.width() <= wrap
    if alt.flow_row_width() > wrap:
        assert abs(alt.block.width() - wrap) <= 2
    # the block itself stays centred in the display
    assert abs(alt.block.geometry().left() - (alt.width() - alt.block.width()) // 2) <= 2

    basic = picker_tab(ak, "Basic")
    alt = visible_alternative(basic)
    assert alt.required_width() <= wrap
    qtbot.waitUntil(lambda: alt.block.width() > 0)
    assert alt.block.width() <= wrap
    assert abs(alt.block.geometry().left() - (alt.width() - alt.block.width()) // 2) <= 2


def test_picker_full_width_in_portrait(qtbot):
    mw, ke = prepared(qtbot, 800, 1100)
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    assert ke.tabbed_keycodes.wrap_width is None
    ak = ke.tabbed_keycodes.all_keycodes
    layers = picker_tab(ak, "Layers")
    alt = visible_alternative(layers)
    qtbot.waitUntil(lambda: alt.block.width() > 0)
    assert alt.block.width() == min(alt.available_width(), max(alt.flow_row_width(), 1))
    # centred when the row is narrower than the page
    if alt.flow_row_width() < alt.available_width():
        assert alt.block.geometry().left() > 1


def test_picker_wrap_follows_resize(qtbot):
    mw, ke = landscape(qtbot)
    assert ke.tabbed_keycodes.wrap_width == mw.height()
    mw.resize(800, 1100)
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    qtbot.waitUntil(lambda: ke.tabbed_keycodes.wrap_width is None)
    mw.resize(1600, 900)
    qtbot.waitUntil(lambda: mw.width() > mw.height())
    qtbot.waitUntil(lambda: ke.tabbed_keycodes.wrap_width == mw.height())
