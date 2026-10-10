# SPDX-License-Identifier: GPL-2.0-or-later
"""Tap Dance and HostOS cards (2026-10-10, docs/entry-chain-spec.md):
- setting one of the four keys from the tray selects the next one (the tray stays open for it); the
  fourth stays selected;
- a "Clear" button at the card's top right sets all four keys to none."""
import os
import sys

from PyQt5.QtCore import Qt

sys.path.insert(0, os.path.dirname(__file__))


def tap_dance(qtbot):
    from test_gui import prepare, find_tab, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, tap_dance=[[4, 5, 6, 7, 200], [0, 0, 0, 0, 300]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw, vk, find_tab(mw, "Tap Dance").editor


def host_os(qtbot):
    from test_gui import prepare, find_tab, FAKE_KEYBOARD_HOST_OS, HOST_OS_MARKER
    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS, tap_dance=[
        [0, 0, 0, 0, 200], [0, 0, 0, 0, 200],
        [0x14, 0x1A, 0x08, 0x15, HOST_OS_MARKER], [0, 0, 0, 0x1B, 500]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw, vk, find_tab(mw, "HostOS").editor


def fields(card):
    from widgets.key_widget import KeyWidget
    return card.findChildren(KeyWidget)


def click(qtbot, w):
    from test_gui import key_pos
    qtbot.mouseClick(w, Qt.LeftButton, pos=key_pos(w))


def pick(kc):
    from tabbed_keycodes import TabbedKeycodes
    TabbedKeycodes.tray.on_tray_keycode_changed(kc)


KEYS = ("KC_A", "KC_B", "KC_C", "KC_D", "KC_E")


def check_chain(qtbot, mw, card):
    from tabbed_keycodes import TabbedKeycodes
    w = fields(card)
    n = len(w)
    click(qtbot, w[0])
    assert TabbedKeycodes.tray.target is w[0]
    for i, kc in enumerate(KEYS[:n - 1]):
        pick(kc)
        assert w[i].keycode == kc
        assert TabbedKeycodes.tray.target is w[i + 1], "the next key is selected"
        assert w[i + 1].active_key is not None and w[i].active_key is None
        assert mw.tray_keycodes.isVisible(), "the tray stays open"
    pick(KEYS[n - 1])
    assert w[n - 1].keycode == KEYS[n - 1]
    assert TabbedKeycodes.tray.target is w[n - 1] and w[n - 1].active_key is not None, "the last stays selected"


def test_tap_dance_moves_to_the_next_key(qtbot):
    mw, vk, tde = tap_dance(qtbot)
    check_chain(qtbot, mw, tde.cards[1])
    assert vk.tap_dance[1] == (4, 5, 6, 7, 300)


def test_host_os_moves_to_the_next_key(qtbot):
    mw, vk, hoe = host_os(qtbot)
    check_chain(qtbot, mw, hoe.cards[1])
    assert vk.tap_dance[3][:4] == (4, 5, 6, 7)


def test_masked_keycode_selects_its_kc_first(qtbot):
    """like the keymap (test_auto_mask.py): a keycode taking a kc selects its kc, then the next key"""
    from tabbed_keycodes import TabbedKeycodes
    mw, vk, tde = tap_dance(qtbot)
    w = fields(tde.cards[1])
    click(qtbot, w[0])
    pick("LT1(kc)")
    assert TabbedKeycodes.tray.target is w[0] and w[0].active_mask, "the kc of the same key"
    pick("KC_C")
    assert w[0].keycode == "LT1(KC_C)"
    assert TabbedKeycodes.tray.target is w[1] and not w[1].active_mask


def check_top_selected(mw, card):
    """after Clear the top key is selected and the tray points at it (2026-10-10)"""
    from tabbed_keycodes import TabbedKeycodes
    w = fields(card)
    assert TabbedKeycodes.tray.target is w[0] and w[0].active_key is not None and not w[0].active_mask
    assert all(f.active_key is None for f in w[1:])
    assert mw.tray_keycodes.isVisible()


def test_clear_button_tap_dance(qtbot):
    from PyQt5.QtWidgets import QPushButton
    mw, vk, tde = tap_dance(qtbot)
    card = tde.cards[0]
    clear = card.clear_button
    assert isinstance(clear, QPushButton) and clear.text() == "Clear"
    # at the top right, on the header line
    assert clear.geometry().right() > card.header.geometry().right() - 5 or clear.x() > card.width() // 2
    assert abs(clear.geometry().center().y() - card.header.geometry().center().y()) <= clear.height()
    qtbot.mouseClick(clear, Qt.LeftButton)
    assert [f.keycode for f in fields(card)] == ["KC_NO"] * 4
    assert vk.tap_dance[0] == (0, 0, 0, 0, 200), "stored, the tapping term untouched"
    check_top_selected(mw, card)


def test_clear_button_host_os(qtbot):
    mw, vk, hoe = host_os(qtbot)
    card = hoe.cards[0]
    qtbot.mouseClick(card.clear_button, Qt.LeftButton)
    assert [f.keycode for f in fields(card)] == ["KC_NO"] * 4
    assert vk.tap_dance[2][:4] == (0, 0, 0, 0)
    check_top_selected(mw, card)


def test_clear_is_translated():
    import xml.etree.ElementTree as ET
    path = os.path.join(os.path.dirname(__file__), "../../resources/base/translations/kert_ja.ts")
    root = ET.parse(path).getroot()
    found = [m.find("translation").text for ctx in root.findall("context") if ctx.find("name").text == "EntryCard"
             for m in ctx.findall("message") if m.find("source").text == "Clear"]
    assert found == ["クリア"]


# ---- Combos: Key 1..4 and the Output key, chained the same way, with a Clear button (2026-10-10)

def combos(qtbot):
    from test_gui import prepare, find_tab, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, combos=[[4, 5, 6, 7, 8], [0, 0, 0, 0, 0]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    return mw, vk, find_tab(mw, "Combos").editor


def test_combos_move_to_the_next_key(qtbot):
    mw, vk, ce = combos(qtbot)
    assert len(fields(ce.cards[1])) == 5
    check_chain(qtbot, mw, ce.cards[1])
    assert vk.combos[1] == (4, 5, 6, 7, 8), "Key 1..4, then the Output key"


def test_clear_button_combos(qtbot):
    mw, vk, ce = combos(qtbot)
    card = ce.cards[0]
    assert card.clear_button is not None and card.clear_button.text() == "Clear"
    qtbot.mouseClick(card.clear_button, Qt.LeftButton)
    assert [f.keycode for f in fields(card)] == ["KC_NO"] * 5
    assert vk.combos[0] == (0, 0, 0, 0, 0)
    check_top_selected(mw, card)
