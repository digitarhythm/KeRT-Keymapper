# SPDX-License-Identifier: GPL-2.0-or-later
"""Less work while the window comes up (docs/web-startup-progress-spec.md, "Finishing", 2026-10-02):
resizes alone do not lay the keyboard out again, the same picker wrap width is not re-applied, and the
picker keys' shadows are painted by their parent in one go instead of by a Python paintEvent per key."""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))


def test_plain_resize_does_not_relayout_the_keyboard(qtbot):
    """the keys' positions do not depend on the widget's size: resizes alone skip update_layout(); a new
    scale does not"""
    from widgets.key_widget import KeyWidget
    w = KeyWidget()
    qtbot.addWidget(w)
    w.show()
    qtbot.waitUntil(w.isVisible)
    count = {"n": 0}
    original = w.update_layout

    def counting():
        count["n"] += 1
        original()
    w.update_layout = counting
    for s in (80, 90, 100):
        w.resize(s, s)
    assert count["n"] == 0
    w.set_scale(1.5)
    w.resize(110, 110)
    assert count["n"] == 1


def test_same_wrap_width_is_a_no_op(qtbot):
    from test_dark_keys import window
    mw = window(qtbot)
    tk = mw.keymap_editor.tabbed_keycodes
    calls = []
    original = tk.all_keycodes.set_wrap_width
    tk.all_keycodes.set_wrap_width = lambda w: (calls.append(w), original(w))
    tk.set_wrap_width(tk.wrap_width)
    assert calls == [], "same width: nothing to do"
    tk.set_wrap_width((tk.wrap_width or 1000) + 50)
    assert len(calls) == 1


def test_picker_key_shadows_painted_by_the_parent(qtbot):
    from widgets.square_button import SquareButton
    from test_dark_keys import window
    assert "paintEvent" not in SquareButton.__dict__, "no Python paintEvent per key button"
    mw = window(qtbot)
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    keys = [b for b in ak.currentWidget().findChildren(SquareButton) if b.isVisible() and b.property("keyButton")]
    assert keys
    assert all(b.parentWidget().property("keyShadowParent") for b in keys)
