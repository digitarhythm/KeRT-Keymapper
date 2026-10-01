# SPDX-License-Identifier: GPL-2.0-or-later
"""The highlight behind the layer buttons (docs/ui-motion-spec.md).

The layer buttons are see-through (stylesheet: QPushButton[layerButton="true"]). This widget sits below
them and paints each button's white face plus one highlight-coloured box, which slides up / down to the
chosen layer with an ease curve instead of jumping. The button the box is over gets white text through
its "lit" property.
"""
import math

from PyQt5.QtCore import QElapsedTimer, QEasingCurve, QEvent, QPropertyAnimation, QRectF, Qt, QTimer, pyqtProperty
from PyQt5.QtGui import QColor, QPainter, QPainterPath, QPalette, QPen
from PyQt5.QtWidgets import QApplication, QWidget

import key_style

SLIDE_MS = 250


class LayerHighlight(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.buttons = []
        self.target = 0
        self._slide = 0.0
        self.animation = QPropertyAnimation(self, b"slide", self)
        self.animation.setDuration(SLIDE_MS)
        self.animation.setEasingCurve(QEasingCurve.InOutCubic)
        # hover: the button under the mouse grows HOVER_GROW_PX per side with an orange frame, like the
        # keymap's keys (KeyboardWidget.enable_hover_zoom); per-button progress 0..1, HOVER_ANIM_MS
        self.hover_index = None
        self.zoom = {}
        self.zoom_timer = QTimer(self)
        self.zoom_timer.setInterval(16)
        self.zoom_timer.timeout.connect(self.step_zoom)
        self.zoom_clock = QElapsedTimer()
        self.hide()

    # --- slide: the box's position as a (fractional) layer index, animated. (Not "pos": that is
    # QWidget's own position property, and animating it would move the whole widget.)

    def get_slide(self):
        return self._slide

    def set_slide(self, value):
        self._slide = value
        self.update_lit()
        self.update()

    slide = pyqtProperty(float, get_slide, set_slide)

    def set_buttons(self, buttons):
        """New layer buttons (a keyboard was loaded): start on layer 0 without animating"""
        for b in self.buttons:
            try:
                b.removeEventFilter(self)
            except RuntimeError:
                pass    # already deleted
        self.animation.stop()
        self.buttons = list(buttons)
        for b in self.buttons:
            b.installEventFilter(self)
        self.hover_index = None
        self.zoom = {}
        self.zoom_timer.stop()
        self.target = 0
        self.set_slide(0.0)
        self.sync_geometry()

    def move_to(self, index):
        """Slide to layer `index`; jumps when nothing is on screen to see it"""
        if not self.buttons:
            return
        index = max(0, min(index, len(self.buttons) - 1))
        if index == self.target and self.animation.state() != QPropertyAnimation.Running:
            if self._slide != index:
                self.set_slide(float(index))
            return
        self.target = index
        self.animation.stop()
        if not self.isVisible():
            self.set_slide(float(index))
            return
        self.animation.setStartValue(self._slide)
        self.animation.setEndValue(float(index))
        self.animation.start()

    # --- geometry: cover the buttons, stay below them

    def eventFilter(self, obj, ev):
        if ev.type() in (QEvent.Move, QEvent.Resize, QEvent.Show, QEvent.Hide):
            self.sync_geometry()
        elif ev.type() == QEvent.Enter and obj in self.buttons:
            self.set_hover(self.buttons.index(obj))
        elif ev.type() == QEvent.Leave and obj in self.buttons and self.hover_index == self.buttons.index(obj):
            self.set_hover(None)
        return False

    # --- hover zoom

    def zoom_progress(self, index):
        return self.zoom.get(index, 0.0)

    def grow(self, index):
        """How far button `index` has grown on each side, in pixels (smoothstep of its progress)"""
        t = self.zoom.get(index, 0.0)
        return key_style.HOVER_GROW_PX * t * t * (3 - 2 * t)

    def update_hovered_labels(self):
        """A button more than half way to white gets a dark label (stylesheet: [hovered="true"])"""
        for i, b in enumerate(self.buttons):
            try:
                t = self.zoom.get(i, 0.0)
                want = t * t * (3 - 2 * t) >= 0.5
                if bool(b.property("hovered")) != want:
                    b.setProperty("hovered", want)
                    b.style().unpolish(b)
                    b.style().polish(b)
                    b.update()
            except RuntimeError:
                pass

    def set_hover(self, index):
        if index == self.hover_index:
            return
        self.hover_index = index
        if index is not None:
            self.zoom.setdefault(index, 0.0)
        if not self.zoom_timer.isActive():
            self.zoom_clock.start()
            self.zoom_timer.start()
        self.step_zoom()

    def step_zoom(self):
        step = self.zoom_clock.restart() / max(1, key_style.HOVER_ANIM_MS)
        for i in list(self.zoom):
            target = 1.0 if i == self.hover_index else 0.0
            p = self.zoom[i]
            p = min(target, p + step) if target > p else max(target, p - step)
            if p <= 0.0 and target == 0.0:
                del self.zoom[i]
            else:
                self.zoom[i] = p
        self.update_hovered_labels()
        if all(v == (1.0 if i == self.hover_index else 0.0) for i, v in self.zoom.items()):
            self.zoom_timer.stop()
        self.update()

    def live_buttons(self):
        live = []
        for b in self.buttons:
            try:
                if b.isVisible():
                    live.append(b)
            except RuntimeError:
                pass
        return live

    def sync_geometry(self):
        buttons = self.live_buttons()
        if not buttons:
            self.hide()
            return
        area = buttons[0].geometry()
        for b in buttons[1:]:
            area = area.united(b.geometry())
        if key_style.DARK_KEYS:
            # room around the buttons for their drop shadows and the hover growth with its frame
            blur, offset = key_style.SHADOW_BLUR, key_style.SHADOW_OFFSET
            m = max(blur, key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH)
            area = area.adjusted(-m, -m, m, m + offset)
        self.setGeometry(area)
        self.lower()
        self.show()
        # which label the box covers depends on where the buttons are: at start-up they are first given
        # to us unplaced (all at the same spot, so every label looked covered) and only then laid out
        self.update_lit()
        self.update()

    def button_rect(self, i):
        g = self.buttons[i].geometry()
        return QRectF(g).translated(-self.x(), -self.y())

    def indicator_rect(self):
        """The highlight box: between the two buttons around the current (fractional) position"""
        n = len(self.buttons)
        lo = max(0, min(int(math.floor(self._slide)), n - 1))
        hi = min(lo + 1, n - 1)
        f = self._slide - lo
        a, b = self.button_rect(lo), self.button_rect(hi)
        return QRectF(a.x() + (b.x() - a.x()) * f, a.y() + (b.y() - a.y()) * f,
                      a.width() + (b.width() - a.width()) * f, a.height() + (b.height() - a.height()) * f)

    def update_lit(self):
        """White text only where the box actually covers the label (the button's centre line); while the
        box is between two buttons neither label is covered, and both stay dark on their white faces"""
        if not self.buttons:
            return
        box = self.indicator_rect()
        for i, b in enumerate(self.buttons):
            try:
                centre = self.button_rect(i).center().y()
                want = box.top() <= centre <= box.bottom()
                if b.property("lit") != want:
                    b.setProperty("lit", want)
                    b.style().unpolish(b)
                    b.style().polish(b)
                    b.update()
            except RuntimeError:
                pass

    def paintEvent(self, ev):
        if not self.live_buttons():
            return
        pal = QApplication.palette()
        r = key_style.CORNER_RADIUS
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        # the buttons' own faces (they are transparent so the box can show through them); in the dark
        # key look black, with the keys' drop shadow under them all first. A hovered button's face is grown
        # and drawn last, so it covers its neighbours
        n = len(self.buttons)
        order = sorted(range(n), key=lambda i: self.zoom.get(i, 0.0))
        faces = {i: self.button_rect(i).adjusted(-self.grow(i), -self.grow(i), self.grow(i), self.grow(i))
                 for i in range(n)}
        if key_style.DARK_KEYS:
            r = key_style.KEY_RADIUS
            for i in order:
                key_style.paint_shadow(p, lambda painter, f=faces[i]: painter.drawRoundedRect(f, r, r))
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(key_style.KEY_FACE))
        else:
            p.setBrush(pal.color(QPalette.Button))
        for i in order:
            if key_style.DARK_KEYS and self.zoom.get(i, 0.0) > 0.0:
                # hovered: fading from the black face to white with the growth
                t = self.zoom[i]
                p.setBrush(key_style.mix(key_style.KEY_FACE, key_style.HOVER_FACE, t * t * (3 - 2 * t)))
            elif key_style.DARK_KEYS:
                p.setBrush(QColor(key_style.KEY_FACE))
            path = QPainterPath()
            path.addRoundedRect(faces[i], r, r)
            p.drawPath(path)
        # the sliding box, grown like the button(s) it is over
        box = self.indicator_rect()
        lo = max(0, min(int(math.floor(self._slide)), n - 1))
        hi = min(lo + 1, n - 1)
        f = self._slide - lo
        g = self.grow(lo) * (1 - f) + self.grow(hi) * f
        p.setBrush(QColor(pal.color(QPalette.Highlight)))
        path = QPainterPath()
        path.addRoundedRect(box.adjusted(-g, -g, g, g), r, r)
        p.drawPath(path)
        # no orange frame here: it marks a selected key on the keymap only (2026-10-02)
        p.end()
