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
    assert isinstance(ke.splitter, RatioSplitter) and SPLIT_RATIO == (4, 6)
    top, bottom = ke.splitter.sizes()
    assert ke.splitter.widget(0) is ke.keyboard_area and ke.splitter.widget(1) is ke.tabbed_keycodes
    # only one picker (the unfiltered one) is visible; the masked-key picker stays hidden until needed
    assert ke.tabbed_keycodes.all_keycodes.isVisible() and ke.tabbed_keycodes.basic_keycodes.isHidden()
    assert abs(top / (top + bottom) - 0.4) < 0.02

    # the ratio survives a window resize
    mw.resize(1600, 1200)
    qtbot.waitUntil(lambda: ke.splitter.height() >= 1000)
    top, bottom = ke.splitter.sizes()
    assert abs(top / (top + bottom) - 0.4) < 0.02


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
    from editor.keymap_editor import picker_wrap_width, PICKER_WRAP_RATIO
    assert PICKER_WRAP_RATIO == 0.75
    wrap = picker_wrap_width(mw.width())
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


def test_keyboard_tab_block_is_wrap_width_not_keyboard_width(qtbot):
    """A tab with a display keyboard (Quantum: the narrow modifier layout) still wraps its buttons at
    the wrap width, so the display keyboard's width is not the limit (2026-09-23)"""
    from editor.keymap_editor import picker_wrap_width

    mw, ke = landscape(qtbot)
    wrap = picker_wrap_width(mw.width())
    ak = ke.tabbed_keycodes.all_keycodes
    quantum = picker_tab(ak, "Quantum")
    alt = visible_alternative(quantum)
    qtbot.waitUntil(lambda: alt.block.width() > 0)
    assert alt.kb_display is not None and alt.required_width() < wrap - 100, "the modifier layout is narrower"
    assert alt.flow_row_width() > wrap, "the Quantum buttons need more than one row"
    qtbot.waitUntil(lambda: abs(alt.block.width() - wrap) <= 2)
    assert abs(alt.block.geometry().left() - (alt.width() - alt.block.width()) // 2) <= 2
    # the display keyboard stays left-aligned inside the block
    assert alt.kb_display.geometry().left() <= 2


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
    from editor.keymap_editor import picker_wrap_width

    mw, ke = landscape(qtbot)
    assert ke.tabbed_keycodes.wrap_width == picker_wrap_width(mw.width())
    mw.resize(800, 1100)
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    qtbot.waitUntil(lambda: ke.tabbed_keycodes.wrap_width is None)
    mw.resize(1600, 900)
    qtbot.waitUntil(lambda: mw.width() > mw.height())
    qtbot.waitUntil(lambda: ke.tabbed_keycodes.wrap_width == picker_wrap_width(mw.width()))


def test_layer_buttons_one_key_left_of_keyboard(qtbot):
    """The layer buttons sit directly left of the keyboard, one key width away, centred with it"""
    mw, ke = prepared(qtbot)
    kb = ke.container

    def buttons():
        # the +/- zoom buttons follow the layer buttons in the list; the list is rebuilt on reconnect
        return ke.layer_buttons[:ke.keyboard.layers]

    # the row re-lays out on the event loop pass after the buttons appear and the keyboard is fitted
    def settled():
        b = buttons()
        return (kb.width > 0 and b and all(x.isVisible() for x in b)
                and ke.layer_column.geometry().width() >= b[0].sizeHint().width()
                and kb.geometry().width() == kb.sizeHint().width()
                and ke.key_gap.geometry().width() == ke.key_gap.sizeHint().width())
    qtbot.waitUntil(settled)
    right = max(b.mapToGlobal(b.rect().topRight()).x() for b in buttons())
    first_key = kb.mapToGlobal(kb.rect().topLeft()).x() + kb.padding
    gap = first_key - right - 1
    expected = ke.key_width_px()
    assert abs(gap - expected) <= 3, (gap, expected)
    # not stuck at the left edge: the group is centred
    left = min(b.mapToGlobal(b.rect().topLeft()).x() for b in buttons())
    area_left = ke.keyboard_area.mapToGlobal(ke.keyboard_area.rect().topLeft()).x()
    assert left - area_left > 100


def settled_layer_column(qtbot, ke):
    """Wait until the row has laid out the (rebuilt) layer buttons, gap and fitted keyboard"""
    kb = ke.container

    def buttons():
        return ke.layer_buttons[:ke.keyboard.layers]

    def ok():
        b = buttons()
        return (kb.width > 0 and b and all(x.isVisible() for x in b)
                and ke.layer_column.geometry().width() >= b[0].sizeHint().width()
                and kb.geometry().width() == kb.sizeHint().width()
                and ke.key_gap.geometry().width() == ke.key_gap.sizeHint().width()
                and ke.left_gap.geometry().width() == ke.row.itemAt(0).geometry().width())
    qtbot.waitUntil(ok)
    return buttons


def test_layer_buttons_align_with_tab_bar(qtbot):
    """When the centred group would put the layer buttons right of the guide (the editor tab bar's left
    edge), the buttons move left onto the guide and the keyboard stays put"""
    mw, ke = prepared(qtbot)
    kb = ke.container
    buttons = settled_layer_column(qtbot, ke)
    left = lambda: min(b.mapToGlobal(b.rect().topLeft()).x() for b in buttons())
    kb_left = lambda: kb.mapToGlobal(kb.rect().topLeft()).x()
    centred_left, kb_at = left(), kb_left()

    # a guide left of the centred position pulls the buttons onto it
    guide = centred_left - 120
    ke.left_guide = lambda: guide
    ke.place_layer_column()
    qtbot.waitUntil(lambda: abs(left() - guide) <= 1)
    assert kb_left() == kb_at
    assert ke.key_gap.sizeHint().width() > ke.key_width_px()

    # a guide right of the centred position changes nothing: the group stays centred
    ke.left_guide = lambda: centred_left + 200
    ke.place_layer_column()
    qtbot.waitUntil(lambda: left() == centred_left)
    assert kb_left() == kb_at
    assert abs(kb_left() + kb.padding - max(b.mapToGlobal(b.rect().topRight()).x() for b in buttons()) - 1
               - ke.key_width_px()) <= 3


def test_layer_button_guide_is_editor_tab_bar(qtbot):
    """The main window points the guide at the left edge of the (centred) editor tab bar"""
    mw, ke = prepared(qtbot)
    bar = mw.tabs.tabBar()
    qtbot.waitUntil(lambda: bar.count() > 0 and bar.isVisible())
    assert ke.left_guide() == bar.mapToGlobal(bar.tabRect(0).topLeft()).x()
    # the tab bar is centred, so its left edge is well inside the window
    assert ke.left_guide() - mw.mapToGlobal(mw.rect().topLeft()).x() > 100
