# SPDX-License-Identifier: GPL-2.0-or-later
"""A translucent black cover with a loading spinner in the middle, over the whole window while something
slow runs - the theme being applied after a pick in the Theme menu (docs/theme-menu-spec.md).

On the desktop it is a widget over the main window (the spinner stands still while the work runs: one
thread). In the browser the page draws it (vialglue.busy -> {cmd: "busy"}, web/src/index.html), and its
spinner keeps turning while the worker is busy.
"""
import sys

from PyQt5.QtCore import QEvent, QRectF, Qt, QTimer
from PyQt5.QtGui import QColor, QPainter, QPen
from PyQt5.QtWidgets import QWidget

COVER = QColor(0, 0, 0, 140)          # the same darkening as the page's start-up cover (rgba(0, 0, 0, 0.55))


class BusyOverlay(QWidget):

    SPINNER_RADIUS = 28
    SPINNER_WIDTH = 6

    def __init__(self, window):
        super().__init__(window)
        self.angle = 0
        self.setGeometry(window.rect())
        window.installEventFilter(self)
        self.timer = QTimer(self)
        self.timer.setInterval(30)
        self.timer.timeout.connect(self.turn)
        self.timer.start()
        self.raise_()

    def eventFilter(self, obj, ev):
        if obj is self.parentWidget() and ev.type() == QEvent.Resize:
            self.setGeometry(obj.rect())
        return False

    def turn(self):
        self.angle = (self.angle + 30) % 360
        self.update()

    def paintEvent(self, ev):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.fillRect(self.rect(), COVER)
        r = self.SPINNER_RADIUS
        ring = QRectF(self.width() / 2 - r, self.height() / 2 - r, 2 * r, 2 * r)
        p.setPen(QPen(QColor(255, 255, 255, 60), self.SPINNER_WIDTH))
        p.drawEllipse(ring)
        pen = QPen(QColor(255, 255, 255), self.SPINNER_WIDTH)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        # a quarter-plus arc, turning (drawArc: 1/16 degree units)
        p.drawArc(ring, -self.angle * 16, 100 * 16)
        p.end()


def set_busy(window, on, web=None):
    """Show (on) or take away the cover over `window`"""
    if web is None:
        web = sys.platform == "emscripten"
    if web:
        import vialglue
        vialglue.busy(1 if on else 0)
        return
    cover = getattr(window, "busy_overlay", None)
    if on:
        if cover is None:
            cover = window.busy_overlay = BusyOverlay(window)
        cover.setGeometry(window.rect())
        cover.raise_()
        cover.show()
        cover.repaint()               # on screen before the slow work starts
    elif cover is not None:
        cover.hide()
