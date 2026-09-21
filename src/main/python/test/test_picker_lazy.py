# SPDX-License-Identifier: GPL-2.0-or-later
"""Keycode picker tabs build their buttons on first show (docs/picker-lazy-build-spec.md §4)."""
import os
import sys

from pytestqt.qt_compat import qt_api

sys.path.insert(0, os.path.dirname(__file__))

MAX_STARTUP_BUTTONS = 2000


def tab_index(ak, label):
    return [x for x in range(ak.count()) if ak.tabText(x) == label][0]


def prepared(qtbot, keyboard=None, **kwargs):
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, keyboard or FAKE_KEYBOARD, **kwargs)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw, vk


def test_startup_builds_only_visible_tab(qtbot):
    from widgets.square_button import SquareButton

    mw, vk = prepared(qtbot)
    assert len(mw.findChildren(SquareButton)) < MAX_STARTUP_BUTTONS

    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    current = ak.currentWidget()
    assert current.label == "Basic" and current.built
    assert [t.label for t in ak.tabs if t.built] == ["Basic"]

    bk = mw.keymap_editor.tabbed_keycodes.basic_keycodes
    assert not any(t.built for t in bk.tabs)
    assert not any(t.built for t in mw.tray_keycodes.all_keycodes.tabs)
    assert not any(t.built for t in mw.tray_keycodes.basic_keycodes.tabs)


def test_tab_builds_when_shown(qtbot):
    from test_gui import find_key_btn

    mw, vk = prepared(qtbot)
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    quantum = ak.tabs[[t.label for t in ak.tabs].index("Quantum")]
    assert not quantum.built and quantum.alternatives == []

    ak.setCurrentIndex(tab_index(ak, "Quantum"))
    assert quantum.built and any(alt.has_buttons() for alt in quantum.alternatives)
    assert find_key_btn(ak, "LSft\n(kc)") is not None
    assert [t.label for t in ak.tabs if t.built] == ["Basic", "Quantum"]


def test_tray_builds_when_opened(qtbot):
    from PyQt5.QtCore import QPoint
    from test_gui import find_tab, find_key_btn, key_pos

    mw, vk = prepared(qtbot, tap_dance=[[4, 5, 6, 7, 200]] * 4)
    tray = mw.tray_keycodes
    assert not tray.isVisible() and not any(t.built for t in tray.all_keycodes.tabs)

    tde = find_tab(mw, "Tap Dance").editor
    mw.tabs.setCurrentWidget(find_tab(mw, "Tap Dance"))
    kc = tde.tap_dance_entries[0].kc_on_tap
    qtbot.waitUntil(lambda: kc.isVisible())
    qtbot.mouseClick(kc, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(kc))
    qtbot.waitUntil(lambda: tray.isVisible())

    built = [t.label for t in tray.all_keycodes.tabs if t.built]
    assert built == [tray.all_keycodes.currentWidget().label]
    assert find_key_btn(tray, "A") is not None


def test_lazy_tab_shows_current_override(qtbot):
    from keymaps import KEYMAPS
    from test_gui import find_key_btn

    mw, vk = prepared(qtbot)
    # portrait and wide: the ISO/JIS tab then shows its full display keyboard (a landscape window wraps
    # the picker at its height and would pick a narrower alternative without the letter keys)
    mw.resize(1700, 1800)
    qtbot.waitUntil(lambda: mw.height() > mw.width())
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    iso = ak.tabs[[t.label for t in ak.tabs].index("ISO/JIS")]
    assert not iso.built

    idx = [name for name, _ in KEYMAPS].index("Colemak")
    mw.change_keyboard_layout(idx)
    override = KEYMAPS[idx][1]
    # a plain letter key that Colemak relabels and that the ISO/JIS tab lists
    qmk_id, label = next((k, v) for k, v in override.items() if k in ("KC_E", "KC_R", "KC_T", "KC_Y"))

    try:
        ak.setCurrentIndex(tab_index(ak, "ISO/JIS"))
        assert iso.built
        assert find_key_btn(ak, label) is not None, "{} should be labelled {} under Colemak".format(qmk_id, label)
    finally:
        mw.change_keyboard_layout(0)   # the layout choice is saved in QSettings: leave QWERTY behind


def test_tab_presence_without_building(qtbot):
    from tabbed_keycodes import keycode_filter_masked

    mw, vk = prepared(qtbot)
    bk = mw.keymap_editor.tabbed_keycodes.basic_keycodes
    assert [bk.tabText(x) for x in range(bk.count())] == ["Basic", "ISO/JIS", "App, Media and Mouse"]
    assert not any(t.built for t in bk.tabs)
    layers = bk.tabs[[t.label for t in bk.tabs].index("Layers")]
    assert not layers.would_have_buttons(keycode_filter_masked)


def test_rebuild_refreshes_built_tab(qtbot):
    mw, vk = prepared(qtbot)
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    basic = ak.currentWidget()
    before = [alt.buttons[0] for alt in basic.alternatives if alt.buttons]
    assert before

    ak.recreate_keycode_buttons()
    assert basic.built
    after = [alt.buttons[0] for alt in basic.alternatives if alt.buttons]
    assert after and all(a is not b for a, b in zip(after, before))
    assert [t.label for t in ak.tabs if t.built] == ["Basic"]
