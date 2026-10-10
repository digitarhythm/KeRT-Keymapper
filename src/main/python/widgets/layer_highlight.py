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
from PyQt5.QtWidgets import QApplication, QPushButton, QWidget

import key_style

# the highlight's slide to the chosen layer; 0 = it jumps there (tried on 2026-10-04, back to the slide,
# now started together with the keymap's rewrite: KeymapEditor.switch_layer)
SLIDE_MS = 250
# start_slide() starts this far in (one frame), so the first paint after the keymap's shows the box moving
SLIDE_START_MS = 16


class LayerHighlight(QWidget):

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.buttons = []
        self.target = 0
        self._slide = 0.0
        self.animation = QPropertyAnimation(self, b"slide", self)
        self.animation.setDuration(SLIDE_MS)
        self.slide_pending = False
        # fast start, slow finish: in the browser the first frame after a click comes ~65 ms later (with the
        # rewritten keymap); an ease-in start left the box still in place there, so it looked late
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        # hover: the button under the mouse grows HOVER_GROW_PX per side with a white frame, like the
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

    def move_to(self, index, later=False):
        """Slide to layer `index`; jumps when nothing is on screen to see it. later: only aim at it, the
        slide starts with start_slide() (KeymapEditor.switch_layer: once the new keymap is painted)"""
        if not self.buttons:
            return
        index = max(0, min(index, len(self.buttons) - 1))
        if index == self.target and self.animation.state() != QPropertyAnimation.Running and not self.slide_pending:
            if self._slide != index:
                self.set_slide(float(index))
            return
        self.target = index
        self.animation.stop()
        if not self.isVisible() or SLIDE_MS <= 0:
            self.slide_pending = False
            self.set_slide(float(index))
            return
        self.slide_pending = True
        if not later:
            self.start_slide()

    def start_slide(self):
        """Start the slide aimed at by move_to(..., later=True), from where the box is now"""
        if not self.slide_pending:
            return
        self.slide_pending = False
        if not self.isVisible():
            self.set_slide(float(self.target))
            return
        self.animation.stop()
        self.animation.setStartValue(self._slide)
        self.animation.setEndValue(float(self.target))
        self.animation.start()
        self.animation.setCurrentTime(min(SLIDE_START_MS, SLIDE_MS))

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

    def paint_order(self):
        """Button indexes in drawing order: the zoomed ones last, the most zoomed on top, and the one under
        the mouse the very last, also while the one it left is still bigger"""
        return sorted(range(len(self.buttons)), key=lambda i: (i == self.hover_index, self.zoom.get(i, 0.0)))

    def zoom_progress(self, index):
        return self.zoom.get(index, 0.0)

    def grow(self, index):
        """How far button `index` has grown on each side, in pixels (smoothstep of its progress)"""
        t = self.zoom.get(index, 0.0)
        return key_style.HOVER_GROW_PX * t * t * (3 - 2 * t)

    def set_hover(self, index):
        if index == self.hover_index:
            return
        self.hover_index = index
        if index is not None:
            self.zoom.setdefault(index, 0.0)
        if key_style.HOVER_ANIM_MS <= 0:
            self.step_zoom()             # no animation: one step to the end, no timer
            return
        if not self.zoom_timer.isActive():
            self.zoom_clock.start()
            self.zoom_timer.start()
        self.step_zoom()

    def step_zoom(self):
        if key_style.HOVER_ANIM_MS <= 0:
            step = 1.0
        else:
            step = self.zoom_clock.restart() / max(1, key_style.HOVER_ANIM_MS)
        for i in list(self.zoom):
            target = 1.0 if i == self.hover_index else 0.0
            p = self.zoom[i]
            p = min(target, p + step) if target > p else max(target, p - step)
            if p <= 0.0 and target == 0.0:
                del self.zoom[i]
            else:
                self.zoom[i] = p
        if all(v == (1.0 if i == self.hover_index else 0.0) for i, v in self.zoom.items()):
            self.zoom_timer.stop()
        self.update_hover_labels()
        self.update()

    def update_hover_labels(self):
        """A grown button's own label is hidden (stylesheet: [hoverLabel="true"]): paintEvent draws it,
        grown with the face"""
        for i, b in enumerate(self.buttons):
            try:
                want = self.zoom.get(i, 0.0) > 0.0
                if bool(b.property("hoverLabel")) != want:
                    b.setProperty("hoverLabel", want)
                    b.style().unpolish(b)
                    b.style().polish(b)
                    b.update()
            except RuntimeError:
                pass

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
        # key look, with the keys' drop shadow under them all first. A hovered button's face is grown and
        # drawn last, so it covers its neighbours, and after the highlight box unless it is the box's button
        n = len(self.buttons)
        order = self.paint_order()
        top = self.hover_index if self.hover_index is not None and self.zoom.get(self.hover_index, 0.0) > 0.0 \
            else None
        if top is not None and (abs(self._slide - top) < 1e-6 or top == self.target):
            # the current layer (the box grows with it) or the box's destination (the clicked button: the
            # sliding box stays on top of it instead of going under it)
            top = None
        faces = {i: self.button_rect(i).adjusted(-self.grow(i), -self.grow(i), self.grow(i), self.grow(i))
                 for i in range(n)}
        if key_style.DARK_KEYS:
            r = key_style.KEY_RADIUS
            # translucent faces: no shadow under any of them (a button's shadow reaches the next one);
            # opaque ones cover it anyway, and the path union is slow
            all_faces = None
            if key_style.KEY_FACE_OPACITY < 1.0:
                all_faces = QPainterPath()
                for f in faces.values():
                    all_faces.addRoundedRect(f, r, r)
                all_faces = all_faces.simplified()
            for i in order:
                key_style.paint_shadow(p, lambda painter, f=faces[i]: painter.drawRoundedRect(f, r, r),
                                       exclude=all_faces)
            p.setPen(Qt.NoPen)
            p.setBrush(key_style.face_color())
        else:
            p.setBrush(pal.color(QPalette.Button))
        face_brush = p.brush()
        for i in order:
            if i == top:
                continue
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
        if top is not None:
            path = QPainterPath()
            path.addRoundedRect(faces[top], r, r)
            if key_style.DARK_KEYS:
                # the faces are translucent: an opaque backdrop in the page colour first, so the buttons and
                # the box under the grown one do not show through it and it reads as the top one
                p.setBrush(self.palette().color(QPalette.Window))
                p.drawPath(path)
            p.setBrush(face_brush)
            p.drawPath(path)
        # a hovered button's white frame, fading in with the growth, like the keymap's hovered key (no orange
        # frame here: it marks a selected key on the keymap only)
        out = key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2
        for i in order:
            t = self.zoom.get(i, 0.0)
            if t <= 0.0:
                continue
            c = QColor(key_style.HOVER_RING_COLOR)
            c.setAlphaF(t * t * (3 - 2 * t))
            p.setPen(QPen(c, key_style.HOVER_FRAME_WIDTH))
            p.setBrush(Qt.NoBrush)
            p.drawRoundedRect(faces[i].adjusted(-out, -out, out, out), key_style.HOVER_FRAME_RADIUS,
                              key_style.HOVER_FRAME_RADIUS)
        # the grown buttons' labels, grown with their faces like the keymap's keys (the buttons' own
        # labels are hidden meanwhile: update_hover_labels)
        for i in order:
            if self.zoom.get(i, 0.0) <= 0.0:
                continue
            b = self.buttons[i]
            plain = self.button_rect(i)
            if plain.width() <= 0 or plain.height() <= 0:
                continue
            p.save()
            p.translate(plain.center())
            p.scale(faces[i].width() / plain.width(), faces[i].height() / plain.height())
            p.translate(-plain.center())
            lit = bool(b.property("lit"))
            colour = pal.color(QPalette.HighlightedText) if lit else (
                QColor(key_style.KEY_LEGEND) if key_style.DARK_KEYS else pal.color(QPalette.ButtonText))
            p.setPen(colour)
            p.setFont(b.font())
            # the label Qt shows (SquareButton's own .text attribute stays empty for SquareButton("2"))
            p.drawText(plain, Qt.AlignCenter, QPushButton.text(b))
            p.restore()
        p.end()
