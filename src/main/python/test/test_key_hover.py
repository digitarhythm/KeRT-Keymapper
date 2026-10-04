# SPDX-License-Identifier: GPL-2.0-or-later
"""Keymap: the key under the mouse grows by key_style.HOVER_GROW_PX on every side, with a white frame, on top of its
neighbours, and stays black; the selected key has an orange frame; other keyboard widgets are unchanged
(docs/dark-keys-spec.md §5)."""
import os
import sys

from PyQt5.QtCore import QEvent, QPoint, QPointF, QRectF, Qt
from PyQt5.QtGui import QColor, QMouseEvent, QPalette
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))

from test_dark_keys import is_face  # noqa: E402


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
    # the grown (still black) face reaches past the key's edge
    assert is_face(QColor(kb.grab().toImage().pixel(*probe)))
    assert not is_face(before), "not part of the key before the mouse came"

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


def is_ring(c):
    """the hover frame's colour (key_style.HOVER_RING_COLOR: black since 2026-10-04, white before)"""
    import key_style
    ring = QColor(key_style.HOVER_RING_COLOR)
    return all(abs(a - b) <= 12 for a, b in ((c.red(), ring.red()), (c.green(), ring.green()), (c.blue(), ring.blue())))


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
    assert key_style.HOVER_ANIM_MS == 0, "no hover animation (2026-10-04 trial; 120 ms before)"


def test_zoom_without_animation(qtbot):
    """no hover animation (2026-10-04 trial: it felt heavy in the browser): the key jumps to its grown
    size when the mouse comes and back when it leaves, with no timer running"""
    kb, key, box, centre = hovered(qtbot)
    move(kb, centre)
    assert kb.zoom_progress(key) == 1.0, "full size at once"
    assert not kb.zoom_timer.isActive()
    move(kb, QPoint(1, 1))
    assert kb.zoom_progress(key) == 0.0, "back at once"
    assert not kb.zoom_timer.isActive()


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


def test_layer_button_hover_without_animation(qtbot):
    ke, hl, buttons = layer_setup(qtbot)
    enter(buttons[1])
    assert hl.hover_index == 1
    assert hl.zoom_progress(1) == 1.0, "full size at once"
    assert not hl.zoom_timer.isActive()
    leave(buttons[1])
    assert hl.hover_index is None
    assert hl.zoom_progress(1) == 0.0, "back at once"
    assert not hl.zoom_timer.isActive()


def test_layer_button_hover_grows_with_white_frame(qtbot):
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
    assert not is_face(QColor(img.pixel(*just_outside)))
    assert not is_orange(QColor(img.pixel(*frame)))
    before_frame = QColor(img.pixel(*frame))
    assert not is_ring(before_frame)
    enter(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    img = shot(parent)
    assert is_face(QColor(img.pixel(*just_outside))), "the (black) face grew"
    assert is_ring(QColor(img.pixel(*frame))), "the hover frame"
    assert not is_orange(QColor(img.pixel(*frame))), "no orange frame (only selected keys get one)"
    leave(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 0.0, timeout=1000)
    img = shot(parent)
    assert not is_orange(QColor(img.pixel(*frame)))
    assert QColor(img.pixel(*frame)) == before_frame, "the frame is gone"


def test_layer_highlight_has_room_for_the_frame(qtbot):
    import key_style
    ke, hl, buttons = layer_setup(qtbot)
    extra = key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH
    for b in buttons:
        assert hl.geometry().contains(b.geometry().adjusted(-extra, -extra, extra, extra))
    # and the "Layer" label above stays clear of the top button's frame
    label = ke.layer_label
    assert label.geometry().bottom() + extra <= buttons[0].geometry().top()


# ---- hovered: stays black, white frame (2026-10-03; replaces "turns white" of 2026-10-02)

def test_hover_ring_constants():
    import key_style
    assert QColor(key_style.HOVER_RING_COLOR) == QColor("#000000"), "black (2026-10-04; white before)"
    for gone in ("HOVER_FACE", "HOVER_LEGEND", "HOVER_OVERRIDE_LEGEND"):
        assert not hasattr(key_style, gone), gone


def test_hovered_key_stays_black(qtbot):
    import key_style
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    inner = (int(left + (right - left) * 0.15), int(top + (bottom - top) * 0.15))   # clear of the legend
    pixel = lambda: QColor(kb.grab().toImage().pixel(*inner))
    assert is_face(pixel())
    move(kb, centre)
    while kb.zoom_progress(key) < 1.0:
        assert is_face(pixel())
        qtbot.wait(5)
    assert is_face(pixel()), "the face colour while hovered"


def test_hovered_key_keeps_its_colours(qtbot):
    import key_style
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    key.text = "A"
    kb.update()
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    img = kb.grab().toImage()
    cx, cy = int((left + right) / 2), int((top + bottom) / 2)
    area = [QColor(img.pixel(x, y)) for x in range(cx - 10, cx + 10) for y in range(cy - 10, cy + 10)]
    face = sum(1 for c in area if is_face(c)) / len(area)
    assert face > 0.5, "mostly the key's own face"
    assert QColor(key_style.KEY_LEGEND) in area, "with its own legend colour on it"


def test_hovered_key_gets_white_frame(qtbot):
    import key_style
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    cy = int((top + bottom) / 2)
    off = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
    grown = (int(left - key_style.HOVER_GROW_PX - off), cy)        # frame around the grown key
    pixel = lambda: QColor(kb.grab().toImage().pixel(*grown))
    before = pixel()
    assert not is_ring(before)
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    assert is_ring(pixel()), "the frame around the grown key"
    move(kb, QPoint(1, 1))
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 0.0, timeout=1000)
    assert pixel() == before, "gone with the hover"


def test_selected_and_hovered_key_shows_orange_frame(qtbot):
    """the selected key's orange frame wins over the hover's white one"""
    import key_style
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    cy = int((top + bottom) / 2)
    off = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
    grown = (int(left - key_style.HOVER_GROW_PX - off), cy)
    move(kb, centre)
    qtbot.mouseClick(kb, Qt.LeftButton, pos=centre)
    assert kb.active_key is key
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    assert is_orange(QColor(kb.grab().toImage().pixel(*grown)))


def test_hovered_layer_button_keeps_its_colours(qtbot):
    import key_style
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    b = buttons[1]
    parent = hl.parentWidget()
    tl = b.mapTo(parent, b.rect().topLeft())
    face = (tl.x() + 6, tl.y() + b.height() // 2)
    assert is_face(QColor(shot(parent).pixel(*face)))
    enter(b)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    img = shot(parent)
    assert is_face(QColor(img.pixel(*face))), "the face colour while hovered"
    assert not b.property("hovered"), "no label colour switch any more"
    label = [QColor(img.pixel(x, y)) for x in range(tl.x() + b.width() // 2 - 6, tl.x() + b.width() // 2 + 6)
             for y in range(tl.y() + b.height() // 2 - 6, tl.y() + b.height() // 2 + 6)]
    legend = QColor(key_style.KEY_LEGEND)
    assert any(abs(c.lightness() - legend.lightness()) < 20 for c in label), "the legend colour on the face"


# ---- the hovered part is on top (2026-10-04)

def test_hovered_key_painted_last(qtbot):
    """the key under the mouse goes on top even while the key it left is still bigger (shrinking back)"""
    kb, key, box, centre = hovered(qtbot)
    other = kb.widgets[1]
    kb.zoom = {other: 0.8, key: 0.2}
    kb.hover_key = key
    order = kb.paint_order()
    assert order[-1] is key
    assert order.index(other) > order.index(kb.widgets[2]), "the shrinking key still above the plain ones"


def test_hovered_layer_button_painted_last(qtbot):
    ke, hl, buttons = layer_setup(qtbot)
    hl.zoom = {0: 0.8, 1: 0.2}
    hl.hover_index = 1
    order = hl.paint_order()
    assert order[-1] == 1
    assert order.index(0) > order.index(2)


def test_hovered_layer_button_over_the_highlight_box(qtbot):
    """a hovered button next to the current layer grows over the highlight box, not under it"""
    import key_style
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    parent = hl.parentWidget()
    b0, b1 = buttons[0], buttons[1]                 # layer 0 is the current one (the box)
    tl0 = b0.mapTo(parent, b0.rect().topLeft())
    tl1 = b1.mapTo(parent, b1.rect().topLeft())
    # inside layer 0's button, just above layer 1's top edge: reached by layer 1's growth
    y = tl1.y() - key_style.HOVER_GROW_PX + 1
    assert y < tl0.y() + b0.height(), "the growth reaches into the current layer's button"
    probe = (tl1.x() + b1.width() // 3, y)
    assert QColor(shot(parent).pixel(*probe)) == QApplication.palette().color(QPalette.Highlight)
    enter(b1)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    assert is_face(QColor(shot(parent).pixel(*probe)), ), "the hovered (green) face on top of the box"


# ---- the hovered face hides what is under it (the faces are translucent; 2026-10-04)

def test_hovered_layer_button_hides_the_next_one(qtbot):
    """over the next button the hovered (translucent) face looks the same as over the page: the button
    under it does not show through, so the hovered one reads as the top one"""
    import key_style
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    parent = hl.parentWidget()
    b1, b2 = buttons[1], buttons[2]
    tl1 = b1.mapTo(parent, b1.rect().topLeft())
    tl2 = b2.mapTo(parent, b2.rect().topLeft())
    y = tl2.y() + 1                                  # inside button 2, reached by button 1's growth
    assert y < tl1.y() + b1.height() + key_style.HOVER_GROW_PX
    probe = (tl2.x() + b2.width() // 3, y)
    enter(b1)
    qtbot.waitUntil(lambda: hl.zoom_progress(1) == 1.0, timeout=1000)
    assert is_face(QColor(shot(parent).pixel(*probe))), QColor(shot(parent).pixel(*probe)).name()


def test_hovered_key_hides_its_neighbour(qtbot, monkeypatch):
    import key_style
    # the test keyboard's keys are 10 px apart: grow further so the hovered key reaches its neighbour
    monkeypatch.setattr(key_style, "HOVER_GROW_PX", 16)
    kb, key, (left, top, right, bottom), centre = hovered(qtbot)
    other = min((k for k in kb.widgets if k is not key and key_box(kb, k)[0] > right),
                key=lambda k: key_box(kb, k)[0])
    oleft, otop, oright, obottom = key_box(kb, other)
    x = int(oleft) + 2                                 # inside the neighbour, reached by the growth
    assert x < right + key_style.HOVER_GROW_PX - 1
    probe = (x, int((top + bottom) / 2))
    move(kb, centre)
    qtbot.waitUntil(lambda: kb.zoom_progress(key) == 1.0, timeout=1000)
    c = QColor(kb.grab().toImage().pixel(*probe))
    assert is_face(c), c.name()


# ---- the picker's key buttons hover like the keymap (2026-10-04)

def picker_setup(qtbot):
    """window, the picker's visible key buttons, the "A" key and its neighbour to the right"""
    from test_dark_keys import window
    from widgets.square_button import SquareButton
    mw = window(qtbot)
    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    qtbot.waitUntil(lambda: any(isinstance(x, SquareButton) and x.isVisible() and x.property("keyButton")
                                for x in ak.currentWidget().findChildren(SquareButton)))
    keys = [x for x in ak.currentWidget().findChildren(SquareButton) if x.isVisible() and x.property("keyButton")]
    a = next(x for x in keys if x.text == "A")
    right = min((x for x in keys if x.parentWidget() is a.parentWidget() and x.y() == a.y() and x.x() > a.x()),
                key=lambda x: x.x())
    return mw, keys, a, right


def face_of(btn, win):
    """the button's face on the window: its rect less KEY_MARGINS"""
    import key_style
    from PyQt5.QtCore import QRect
    tl = btn.mapTo(win, btn.rect().topLeft())
    l, t, r, b = key_style.KEY_MARGINS
    return QRect(tl.x() + l, tl.y() + t, btn.width() - l - r, btn.height() - t - b)


def test_picker_has_no_hover_colour(qtbot):
    """the face no longer turns a deeper green under the mouse: it grows instead"""
    import branding_theme
    import themes
    branding_theme.register()
    themes.Theme.set_theme("KeRT Color")
    assert 'QPushButton[keyButton="true"]:hover' not in QApplication.instance().styleSheet()


def test_picker_key_grows_with_white_frame(qtbot):
    import key_style
    mw, keys, a, right = picker_setup(qtbot)
    win = a.window()
    f = face_of(a, win)
    y = f.center().y()
    just_outside = (f.left() - 2, y)
    off = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
    frame = (int(f.left() - key_style.HOVER_GROW_PX - off), y)
    pixel = lambda p: QColor(win.grab().toImage().pixel(*p))
    before_frame = pixel(frame)
    assert not is_face(pixel(just_outside)) and not is_ring(before_frame)
    enter(a)
    a.update()
    assert is_face(pixel(just_outside)), "the face grew past its edge"
    assert is_ring(pixel(frame)), "the frame around the grown face"
    leave(a)
    assert not is_face(pixel(just_outside)) and pixel(frame) == before_frame, "back to normal"


def test_picker_hovered_key_on_top(qtbot, monkeypatch):
    """the grown key and its frame are drawn over the neighbouring buttons"""
    import key_style
    mw, keys, a, right = picker_setup(qtbot)
    win = a.window()
    fa, fr = face_of(a, win), face_of(right, win)
    # the picker's faces are further apart than the growth: grow as far as the gap so the frame lands on
    # the neighbour's face
    monkeypatch.setattr(key_style, "HOVER_GROW_PX", fr.left() - fa.right())
    off = key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
    x = int(fa.right() + off)                            # the frame's right side ...
    assert fr.left() < x < fr.right(), "... lies on the neighbour's face"
    probe = (x, fa.center().y())
    enter(a)
    assert is_ring(QColor(win.grab().toImage().pixel(*probe))), "frame over the neighbour"


def test_picker_hovered_key_keeps_its_legend(qtbot):
    mw, keys, a, right = picker_setup(qtbot)
    win = a.window()
    f = face_of(a, win)
    enter(a)
    img = win.grab().toImage()
    area = [QColor(img.pixel(x, y)) for x in range(f.center().x() - 8, f.center().x() + 8)
            for y in range(f.center().y() - 8, f.center().y() + 8)]
    assert any(c.lightness() < 90 for c in area), "the dark legend is drawn on the grown face"
    assert sum(1 for c in area if is_face(c)) > len(area) // 3, "on the key's own face colour"


def test_picker_has_room_for_edge_keys(qtbot):
    """the overlay paints over the picker's page (around the block), which leaves room around every key
    for the grown face and its frame, so the keys on the block's edges are not cut off"""
    import key_style
    mw, keys, a, right = picker_setup(qtbot)
    host = a.parentWidget()                             # the page around the block holds the overlay
    while host is not None and getattr(host, "key_hover_overlay", None) is None:
        host = host.parentWidget()
    assert host is not None and host is not a.parentWidget(), "over a widget around the block"
    overlay = host.key_hover_overlay
    assert overlay.parentWidget() is host
    frame = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH
    for btn in (x for x in keys if x.parentWidget() is a.parentWidget()):
        f = overlay.face(btn).adjusted(-frame, -frame, frame, frame)
        assert QRectF(host.rect()).contains(f), btn.text


def test_sliding_box_goes_over_its_hovered_target(qtbot):
    """The clicked (hovered) button is the box's destination: while the box slides there it stays on top
    of that button, instead of disappearing under it (2026-10-04)"""
    from test_dark_keys import shot
    ke, hl, buttons = layer_setup(qtbot)
    parent = hl.parentWidget()
    enter(buttons[2])
    qtbot.waitUntil(lambda: hl.zoom_progress(2) == 1.0, timeout=1000)
    hl.animation.stop()
    hl.target = 2
    hl.set_slide(1.6)                       # on its way from layer 1 to layer 2
    box = hl.indicator_rect()
    b2 = buttons[2]
    top2 = b2.mapTo(parent, b2.rect().topLeft()).y()
    probe_y = int(hl.mapTo(parent, box.bottomLeft().toPoint()).y()) - 3      # the box's lower part ...
    assert probe_y > top2 + 2, "... lies over button 2"
    x = b2.mapTo(parent, b2.rect().topLeft()).x() + b2.width() // 3
    assert QColor(shot(parent).pixel(x, probe_y)) == QApplication.palette().color(QPalette.Highlight)
