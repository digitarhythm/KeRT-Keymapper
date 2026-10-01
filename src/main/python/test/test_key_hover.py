# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap: the key under the mouse grows by key_style.HOVER_GROW_PX on every side, with an orange frame, on top of its
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


def test_hover_grow_constant():
    """the hovered key grows by the same few pixels on every side, whatever its size (2026-10-02: a
    percentage made wide keys grow far sideways and pushed edge keys' frames out of the widget)"""
    import key_style
    assert 3 <= key_style.HOVER_GROW_PX <= 8


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
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    # the grown face reaches past the key's edge (white while hovered)
    assert QColor(kb.grab().toImage().pixel(*probe)) == QColor(key_style.HOVER_FACE)
    assert before != QColor(key_style.KEY_FACE), "not part of the key before the mouse came"

    # off the keys again: back to normal
    move(kb, QPoint(1, 1))
    assert kb.hover_key is None
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 0.0, timeout=1000)
    assert QColor(kb.grab().toImage().pixel(*probe)) == before


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



# ---- animation and the orange frame (2026-10-02)

def is_orange(c):
    return c.red() > 200 and 90 <= c.green() <= 190 and c.blue() < 90


def hovered(qtbot, index=0):
    from test_dark_keys import window
    mw = window(qtbot)
    kb = mw.keymap_editor.container
    key = kb.widgets[index]
    left, top, right, bottom = key_box(kb, key)
    return kb, key, (left, top, right, bottom), QPoint(int((left + right) / 2), int((top + bottom) / 2))


def test_frame_and_animation_constants():
    import key_style
    assert key_style.HOVER_FRAME_RADIUS == 10
    assert is_orange(QColor(key_style.HOVER_FRAME_COLOR))
    assert 2 <= key_style.HOVER_FRAME_WIDTH <= 4
    assert 80 <= key_style.HOVER_ANIM_MS <= 250


def test_zoom_animates_in_and_out(qtbot):
    from PyQt5.QtCore import QElapsedTimer
    import key_style

    kb, key, box, centre = hovered(qtbot)
    clock = QElapsedTimer()
    clock.start()
    move(kb, centre)
    assert kb.zoom_progress(key) < 1.0, "does not jump to full size"
    seen = set()
    while kb.zoom_progress(key) < 1.0 and clock.elapsed() < 2000:
        seen.add(round(kb.zoom_progress(key), 2))
        qtbot.wait(5)
    assert kb.zoom_progress(key) == 1.0
    assert any(0.0 < v < 1.0 for v in seen), "passes through in-between sizes"
    assert clock.elapsed() >= key_style.HOVER_ANIM_MS * 0.6

    move(kb, QPoint(1, 1))
    assert kb.zoom_progress(key) > 0.0, "shrinks back gradually too"
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 0.0, timeout=2000)


def test_orange_frame_only_on_the_selected_key(qtbot):
    """the orange frame marks the clicked (selected) key, not the hovered one (2026-10-02)"""
    import key_style

    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    cy = int((top + bottom) / 2)
    off = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
    plain = (int(left - off), cy)                                  # frame around the key at normal size
    grown = (int(left - key_style.HOVER_GROW_PX - off), cy)        # frame around the grown key
    pixel = lambda p: QColor(kb.grab().toImage().pixel(*p))

    assert not is_orange(pixel(plain))
    # hovering grows the key, without a frame
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    assert not is_orange(pixel(grown)) and not is_orange(pixel(plain))
    # clicking selects it: the frame appears around the (grown) key
    qtbot.mouseClick(kb, Qt.LeftButton, pos=centre)
    assert kb.active_key is key
    qtbot.waitUntil(lambda: is_orange(pixel(grown)), timeout=1000)
    # the mouse leaves: the key shrinks back, the frame stays around the selected key
    move(kb, QPoint(1, 1))
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 0.0, timeout=1000)
    assert is_orange(pixel(plain))
    # deselected: no frame
    kb.deselect()
    qtbot.waitUntil(lambda: not is_orange(pixel(plain)), timeout=1000)


def test_other_keyboard_widgets_have_no_frame(qtbot):
    """the frame belongs to the keymap (hover_zoom); single-key widgets in the editors do not get it"""
    import key_style
    from widgets.key_widget import KeyWidget
    from test_dark_keys import themed
    themed()
    w = KeyWidget()
    w.set_keycode("KC_A")
    qtbot.addWidget(w)
    w.resize(w.minimumSizeHint())
    w.active_key = w.widgets[0]
    img = w.grab().toImage()
    assert not any(is_orange(QColor(img.pixel(x, y))) for x in range(img.width()) for y in range(img.height()))


def test_animation_repaints_only_around_the_key(qtbot):
    """each animation frame asks for a repaint of the moving key's area only, not the whole keyboard"""
    kb, key, box, centre = hovered(qtbot)
    rects = []
    original = kb.update

    def recording_update(*args):
        rects.append(args[0] if args else None)
        return original(*args)
    kb.update = recording_update
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    frames = [r for r in rects if r is not None]
    assert frames and None not in rects[1:], rects
    whole = kb.rect()
    assert all(r.width() * r.height() < whole.width() * whole.height() / 2 for r in frames)



def test_frame_fits_inside_the_widget_for_edge_keys(qtbot):
    """the keymap leaves room around the keys for the grown key and its frame, so keys at the edges
    (top row, last column) are not cut off"""
    import key_style
    from test_dark_keys import window
    mw = window(qtbot)
    kb = mw.keymap_editor.container
    extra = key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH
    size = kb.size()
    for key in kb.widgets:
        left, top, right, bottom = key_box(kb, key)
        assert left - extra >= 0 and top - extra >= 0, key
        assert right + extra <= size.width() and bottom + extra <= size.height(), key


# ---- layer buttons hover the same way (2026-10-02)

def layer_setup(qtbot):
    from test_dark_keys import window
    mw = window(qtbot)
    ke = mw.keymap_editor
    return ke, ke.layer_highlight, ke.layer_buttons[:ke.keyboard.layers]


def enter(widget):
    QApplication.sendEvent(widget, QEvent(QEvent.Enter))


def leave(widget):
    QApplication.sendEvent(widget, QEvent(QEvent.Leave))


def test_layer_button_hover_animates(qtbot):
    from PyQt5.QtCore import QElapsedTimer
    ke, hl, buttons = layer_setup(qtbot)
    clock = QElapsedTimer()
    clock.start()
    enter(buttons[1])
    assert hl.hover_index == 1
    assert hl.zoom_progress(1) < 1.0, "does not jump"
    seen = set()
    while hl.zoom_progress(1) < 1.0 and clock.elapsed() < 2000:
        seen.add(round(hl.zoom_progress(1), 2))
        qtbot.wait(5)
    assert hl.zoom_progress(1) == 1.0 and any(0 < v < 1 for v in seen)
    leave(buttons[1])
    assert hl.hover_index is None
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 0.0, timeout=2000)


def test_layer_button_hover_grows_without_frame(qtbot):
    import key_style
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    b = buttons[1]                               # not the current layer: black face
    parent = hl.parentWidget()
    tl = b.mapTo(parent, b.rect().topLeft())
    y = tl.y() + b.height() // 2
    just_outside = (tl.x() - 2, y)
    frame = (int(tl.x() - key_style.HOVER_GROW_PX - key_style.HOVER_FRAME_GAP - key_style.HOVER_FRAME_WIDTH / 2), y)

    img = shot(parent)
    assert QColor(img.pixel(*just_outside)) != QColor(key_style.KEY_FACE)
    assert not is_orange(QColor(img.pixel(*frame)))
    enter(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    img = shot(parent)
    assert QColor(img.pixel(*just_outside)) == QColor(key_style.HOVER_FACE), "the face grew (white while hovered)"
    assert not is_orange(QColor(img.pixel(*frame))), "no frame on hover (only selected keys get one)"
    leave(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 0.0, timeout=1000)
    img = shot(parent)
    assert not is_orange(QColor(img.pixel(*frame)))


def test_layer_highlight_has_room_for_the_frame(qtbot):
    import key_style
    ke, hl, buttons = layer_setup(qtbot)
    extra = key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH
    for b in buttons:
        assert hl.geometry().contains(b.geometry().adjusted(-extra, -extra, extra, extra))
    # and the "Layer" label above stays clear of the top button's frame
    label = ke.layer_label
    assert label.geometry().bottom() + extra <= buttons[0].geometry().top()


# ---- white while hovered (2026-10-02)

def test_hover_colours_constants():
    import key_style
    assert QColor(key_style.HOVER_FACE) == QColor("#ffffff")
    assert QColor(key_style.HOVER_LEGEND) == QColor("#000000")
    mid = key_style.mix(key_style.KEY_FACE, key_style.HOVER_FACE, 0.5)
    assert 100 < mid.lightness() < 160


def test_hovered_key_turns_white(qtbot):
    import key_style
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    inner = (int(left + (right - left) * 0.15), int(top + (bottom - top) * 0.15))   # clear of the legend
    pixel = lambda: QColor(kb.grab().toImage().pixel(*inner))
    assert pixel() == QColor(key_style.KEY_FACE)
    move(kb, centre)
    seen = []
    while kb.zoom_progress(key) < 1.0:
        seen.append(pixel().lightness())
        qtbot.wait(5)
    assert pixel() == QColor(key_style.HOVER_FACE), "white while hovered"
    assert any(0 < v < 255 for v in seen), "fades through grey"
    move(kb, QPoint(1, 1))
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 0.0, timeout=1000)
    assert pixel() == QColor(key_style.KEY_FACE)


def test_hovered_key_legend_turns_dark(qtbot):
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    key.text = "A"
    kb.update()
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    img = kb.grab().toImage()
    cx, cy = int((left + right) / 2), int((top + bottom) / 2)
    area = [QColor(img.pixel(x, y)).lightness() for x in range(cx - 10, cx + 10) for y in range(cy - 10, cy + 10)]
    bright = sum(1 for v in area if v > 240) / len(area)
    assert bright > 0.5, "mostly the white face"
    assert min(area) < 80, "with a dark legend on it"


def test_hovered_layer_button_turns_white(qtbot):
    import key_style
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    b = buttons[1]
    parent = hl.parentWidget()
    tl = b.mapTo(parent, b.rect().topLeft())
    face = (tl.x() + 6, tl.y() + b.height() // 2)
    assert QColor(shot(parent).pixel(*face)) == QColor(key_style.KEY_FACE)
    enter(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    img = shot(parent)
    assert QColor(img.pixel(*face)) == QColor(key_style.HOVER_FACE)
    assert b.property("hovered") is True
    label = [QColor(img.pixel(x, y)).lightness() for x in range(tl.x() + b.width() // 2 - 6, tl.x() + b.width() // 2 + 6)
             for y in range(tl.y() + b.height() // 2 - 6, tl.y() + b.height() // 2 + 6)]
    assert min(label) < 100, "dark label on the white face"
    leave(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 0.0, timeout=1000)
    assert QColor(shot(parent).pixel(*face)) == QColor(key_style.KEY_FACE)
    assert not b.property("hovered")
