# SPDX-License-Identifier: GPL-2.0-or-later
"""The picker's key buttons hover like the keymap's keys (docs/dark-keys-spec.md 5.6): the button under
the mouse is drawn HOVER_GROW_PX larger on every side, with a white frame, on top of its neighbours.

A button cannot paint outside its own rectangle and its later siblings paint over it, so a transparent
overlay over the buttons' parent (raised above them, letting the mouse through) paints the hovered one:
shadow, an opaque backdrop in the page colour (the faces are translucent), the face, the legend, the frame.
"""
from PyQt5 import sip
from PyQt5.QtCore import QEvent, QPoint, QRectF, Qt
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget

import key_style



def room():
    """Space to leave above and below the key buttons: the overlay sits on the page around the buttons'
    block (so it can paint past the block's left and right edges), but the block starts right at the top
    of the page"""
    if not key_style.DARK_KEYS:
        return 0
    return key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH


def backdrop_colour(widget):
    """What shows behind `widget`: the background of the nearest ancestor that fills its own"""
    w = widget
    while w is not None:
        if w.autoFillBackground():
            return w.palette().color(w.backgroundRole())
        w = w.parentWidget()
    return QApplication.palette().color(QPalette.Window)


def legend_of(btn):
    if getattr(btn, "label", None) is not None and not sip.isdeleted(btn.label):
        return btn.label.text()
    text = btn.text if isinstance(btn.text, str) else btn.text()
    return text.replace("&&", "&")


def legend_colour(btn):
    from util import KeycodeDisplay
    keycode = getattr(btn, "keycode", None)
    if keycode is not None and keycode.qmk_id in KeycodeDisplay.keymap_override:
        return key_style.override_color()
    return QColor(key_style.KEY_LEGEND)


def overlay_for(btn):
    """The overlay painting `btn`'s hover: on the nearest widget around it that has one"""
    w = btn.parentWidget()
    while w is not None:
        overlay = getattr(w, "key_hover_overlay", None)
        if overlay is not None and not sip.isdeleted(overlay):
            return overlay
        w = w.parentWidget()
    return None


class KeyHoverOverlay(QWidget):
    """Over `host`, painting the hovered key button inside it. The buttons report their own Enter / Leave
    (SquareButton.enterEvent ...): an event filter on every button would run Python for each of their
    events, which made the browser build's start-up much slower"""

    def __init__(self, host):
        super().__init__(host)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.hovered = None
        self.setGeometry(host.rect())
        host.installEventFilter(self)
        self.raise_()
        self.show()

    def face(self, btn):
        """The hovered button's grown face, in this overlay's coordinates"""
        left, top, right, bottom = key_style.KEY_MARGINS
        g = key_style.HOVER_GROW_PX
        tl = btn.mapTo(self.parentWidget(), QPoint(0, 0))
        return QRectF(tl.x(), tl.y(), btn.width(), btn.height()).adjusted(left - g, top - g, -right + g, -bottom + g)

    def dirty(self, btn):
        m = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH + key_style.SHADOW_OFFSET \
            + key_style.SHADOW_BLUR + 2
        return self.face(btn).adjusted(-m, -m, m, m).toAlignedRect()

    def set_hovered(self, btn):
        if btn is self.hovered:
            return
        if self.hovered is not None and not sip.isdeleted(self.hovered):
            self.update(self.dirty(self.hovered))
        self.hovered = btn
        if btn is not None:
            self.raise_()
            self.update(self.dirty(btn))

    def eventFilter(self, obj, ev):
        if obj is self.parentWidget():
            if ev.type() == QEvent.Resize:
                self.setGeometry(obj.rect())
            elif ev.type() == QEvent.ChildAdded:
                self.raise_()
        return False

    def button_entered(self, btn):
        self.set_hovered(btn if btn.isEnabled() and btn.property("keyButton") else None)

    def button_left(self, btn):
        if btn is self.hovered:
            self.set_hovered(None)

    def button_changed(self, btn):
        if btn is self.hovered:
            self.update(self.dirty(btn))

    def paintEvent(self, ev):
        btn = self.hovered
        if btn is None or sip.isdeleted(btn) or not btn.isVisible() or not key_style.DARK_KEYS:
            return
        face = self.face(btn)
        r = key_style.KEY_RADIUS
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        key_style.paint_shadow(p, lambda painter: painter.drawRoundedRect(face, r, r))
        path = QPainterPath()
        path.addRoundedRect(face, r, r)
        p.setPen(Qt.NoPen)
        pal = QApplication.palette()
        if btn.isDown():
            p.setBrush(pal.color(QPalette.Highlight))
            p.drawPath(path)
            text = pal.color(QPalette.HighlightedText)
        else:
            # the faces are translucent: an opaque backdrop first, so nothing under the grown face shows
            p.setBrush(backdrop_colour(self.parentWidget()))
            p.drawPath(path)
            p.setBrush(key_style.face_color())
            p.drawPath(path)
            text = legend_colour(btn)
        # the legend grows with the face, like the keymap's hovered key (KeyboardWidget.key_transform):
        # drawn in the button's own face rect, scaled about its centre by the face's growth
        plain = face.adjusted(key_style.HOVER_GROW_PX, key_style.HOVER_GROW_PX,
                              -key_style.HOVER_GROW_PX, -key_style.HOVER_GROW_PX)
        p.save()
        if plain.width() > 0 and plain.height() > 0:
            p.translate(plain.center())
            p.scale(face.width() / plain.width(), face.height() / plain.height())
            p.translate(-plain.center())
        p.setPen(text)
        p.setFont(btn.font())
        p.drawText(plain, Qt.AlignCenter | Qt.TextWordWrap, legend_of(btn))
        p.restore()
        out = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
        p.setPen(QPen(QColor(key_style.HOVER_RING_COLOR), key_style.HOVER_FRAME_WIDTH))
        p.setBrush(Qt.NoBrush)
        p.drawRoundedRect(face.adjusted(-out, -out, out, out), key_style.HOVER_FRAME_RADIUS,
                          key_style.HOVER_FRAME_RADIUS)
        p.end()


def install(host):
    """Let the key buttons inside `host` hover like the keymap's keys, painted over `host` (once)"""
    if host is None or not key_style.DARK_KEYS:
        return None
    overlay = getattr(host, "key_hover_overlay", None)
    if overlay is None or sip.isdeleted(overlay):
        overlay = KeyHoverOverlay(host)
        host.key_hover_overlay = overlay
    return overlay
