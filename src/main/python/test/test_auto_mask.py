# SPDX-License-Identifier: GPL-2.0-or-later
"""A keycode that takes a "kc" (LT1(kc), LCTL_T(kc), LCTL(kc) ... from the Layers / Quantum tabs) put on a
key selects that key's inner "kc" part at once, so the next pick fills it; then the selection moves on to
the next key as usual (2026-10-10, docs/auto-mask-spec.md)."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def editor(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    ke = mw.keymap_editor
    c = ke.container
    c.active_key, c.active_mask = c.widgets[1], False
    ke.on_key_clicked()
    return mw, vk, ke, c


def layout(ke, widget):
    return ke.keyboard.layout[(ke.current_layer, widget.desc.row, widget.desc.col)]


def test_masked_keycode_selects_its_kc(qtbot):
    mw, vk, ke, c = editor(qtbot)
    key = c.widgets[1]
    ke.set_key("LT1(kc)")
    assert layout(ke, key) == "LT1(kc)"
    assert c.active_key is key and c.active_mask, "the same key's inner kc is selected"
    tk = ke.tabbed_keycodes
    assert tk.basic_keycodes.isVisible() and not tk.all_keycodes.isVisible(), "the picker offers basic keys"
    # the next pick fills the kc, then the selection moves on to the next key
    ke.set_key("KC_C")
    assert layout(ke, key) == "LT1(KC_C)"
    assert c.active_key is c.widgets[2] and not c.active_mask
    assert tk.all_keycodes.isVisible() and not tk.basic_keycodes.isVisible()


def test_mod_tap_and_modifier_keycodes_too(qtbot):
    mw, vk, ke, c = editor(qtbot)
    for code in ("LCTL_T(kc)", "LCTL(kc)"):
        c.active_key, c.active_mask = c.widgets[1], False
        ke.set_key(code)
        assert c.active_key is c.widgets[1] and c.active_mask, code


def test_plain_keycode_moves_on(qtbot):
    mw, vk, ke, c = editor(qtbot)
    ke.set_key("KC_A")
    assert c.active_key is c.widgets[2] and not c.active_mask
