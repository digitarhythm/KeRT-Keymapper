# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap: the key under the mouse is drawn slightly larger (key_style.HOVER_SCALE) and on top of its
neighbours; other keyboard widgets are unchanged (docs/dark-keys-spec.md §5)."""
import os
import sys

from PyQt5.QtCore import QEvent, QPoint, QPointF, Qt
from PyQt5.QtGui import QColor, QMouseEvent
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))


def move(widget, pos):
    ev = QMouseEvent(QEvent.MouseMove, QPointF(pos), Qt.NoButton, Qt.NoButton, Qt.NoModifier)
    QApplication.sendEvent(widget, ev)


def key_box(kb, key):
    """the key's rectangle on screen"""
    r = key.polygon.boundingRect()
    return (r.left() * kb.scale, r.top() * kb.scale, r.right() * kb.scale, r.bottom() * kb.scale)


def test_hover_scale_constant():
    import key_style
    assert 1.03 <= key_style.HOVER_SCALE <= 1.15, "slightly larger"


def test_keymap_key_grows_under_the_mouse(qtbot):
    import key_style
    from test_dark_keys import window

    mw = window(qtbot)
    kb = mw.keymap_editor.container
    assert kb.hover_zoom
    key = kb.widgets[0]
    left, top, right, bottom = key_box(kb, key)
    centre = QPoint(int((left + right) / 2), int((top + bottom) / 2))
    probe = (int(left) - 2, int((top + bottom) / 2))      # just outside the key's left edge

    before = QColor(kb.grab().toImage().pixel(*probe))
    move(kb, centre)
    assert kb.hover_key is key
    qtbot.waitUntil(lambda: QColor(kb.grab().toImage().pixel(*probe)) == QColor(key_style.KEY_FACE), timeout=1000)
    assert before != QColor(key_style.KEY_FACE), "not part of the key before the mouse came"

    # off the keys again: back to normal
    move(kb, QPoint(1, 1))
    assert kb.hover_key is None
    qtbot.waitUntil(lambda: QColor(kb.grab().toImage().pixel(*probe)) == before, timeout=1000)


def test_leaving_the_widget_drops_the_hover(qtbot):
    from test_dark_keys import window
    mw = window(qtbot)
    kb = mw.keymap_editor.container
    key = kb.widgets[0]
    left, top, right, bottom = key_box(kb, key)
    move(kb, QPoint(int((left + right) / 2), int((top + bottom) / 2)))
    assert kb.hover_key is key
    QApplication.sendEvent(kb, QEvent(QEvent.Leave))
    assert kb.hover_key is None


def test_other_keyboard_widgets_do_not_zoom(qtbot):
    from widgets.key_widget import KeyWidget
    w = KeyWidget()
    qtbot.addWidget(w)
    assert not w.hover_zoom
    move(w, QPoint(10, 10))
    assert w.hover_key is None
