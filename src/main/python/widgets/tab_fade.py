# SPDX-License-Identifier: GPL-2.0-or-later
"""Fade between tab pages when a tab is clicked (docs/ui-motion-spec.md).

A click on a tab no longer switches at once: the old page fades out, the tab switches, and the new
page fades in, FADE_OUT_MS + FADE_IN_MS = 0.3 s in total. Only mouse clicks fade; keyboard navigation
and setCurrentIndex() from code switch immediately, so nothing else changes behaviour.

Browser build: Qt paints in software there, and even a single-pixmap crossfade of a whole page drew
3 frames in 0.35 s (measured), which looks like a plain jump. There the page does the fade instead: a
box over the page area animated with CSS (vialglue.fade, web/src/index.html), composited by the
browser on the GPU. Python only says "out", switches the tab under the covered area, and says "in".

Desktop: the fade is drawn by an overlay above the page stack, never by re-rendering the pages: repainting a
page (the keymap page has hundreds of buttons and a Python-painted keyboard) on every frame is slow on
the desktop and far too slow in the browser build, where the fade then showed as a plain jump. The
overlay takes one picture of the old page and fades it into the background colour; after the switch
it takes one picture of the new page and fades it in from the background colour. It paints every pixel
itself (WA_OpaquePaintEvent), so nothing under it is repainted while it is up: each frame is one fill
and one pixmap.
"""
import os
import sys

from PyQt5.QtCore import QElapsedTimer, QEasingCurve, QEvent, QObject, QPropertyAnimation, Qt, QTimer, pyqtProperty
from PyQt5.QtGui import QPainter, QPalette
from PyQt5.QtWidgets import QStackedWidget, QTabWidget, QWidget

FADE_OUT_MS = 150
FADE_IN_MS = 150
PROPERTY = "kertTabFade"
WEB = sys.platform == "emscripten"
# KERT_DEBUG_MOTION=1 (browser: open the page with ?debug=motion) prints each fade's timing and frames
DEBUG = bool(os.environ.get("KERT_DEBUG_MOTION"))


def debug(*args):
    if DEBUG:
        print("[motion]", *args, flush=True)


class FadeOverlay(QWidget):
    """Covers the page stack while fading. cover = 0: see-through, 1: only the background colour."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_OpaquePaintEvent)       # paintEvent covers every pixel
        self.snapshot = None
        self._cover = 0.0
        self.frames = 0
        self.hide()

    def get_cover(self):
        return self._cover

    def set_cover(self, value):
        self._cover = value
        self.update()

    cover = pyqtProperty(float, get_cover, set_cover)

    def paintEvent(self, ev):
        # the page picture over the background colour: fainter as cover grows (fade-out of the old page),
        # stronger as it shrinks (fade-in of the new one); with no picture, just the background
        self.frames += 1
        p = QPainter(self)
        p.fillRect(self.rect(), self.palette().color(QPalette.Window))
        if self.snapshot is not None:
            p.setOpacity(1.0 - self._cover)
            p.drawPixmap(0, 0, self.snapshot)
        p.end()


class TabFader(QObject):

    def __init__(self, tabs):
        super().__init__(tabs)
        self.tabs = tabs
        self.stack = tabs.findChild(QStackedWidget, "qt_tabwidget_stackedwidget", Qt.FindDirectChildrenOnly)
        self.bar = tabs.tabBar()
        self.bar.installEventFilter(self)
        self.overlay = FadeOverlay(tabs)
        self.pending = None
        self.phase = None           # "out", "switching", "in" or None
        self.animation = QPropertyAnimation(self.overlay, b"cover", self)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.finished.connect(self.on_finished)
        self.clock = QElapsedTimer()
        self.generation = 0         # stale single-shot timers of an abandoned fade compare this
        debug("fader on", type(tabs).__name__, "stack" if self.stack is not None else "NO STACK")

    def eventFilter(self, obj, ev):
        if obj is self.bar and ev.type() == QEvent.MouseButtonPress and ev.button() == Qt.LeftButton:
            index = self.bar.tabAt(ev.pos())
            debug("press on", type(self.tabs).__name__, "tab", index, "current", self.tabs.currentIndex(),
                  "visible", self.tabs.isVisible())
            if index >= 0 and self.bar.isTabEnabled(index) and index != self.tabs.currentIndex() \
                    and self.stack is not None and self.tabs.isVisible():
                self.fade_to(index)
                return True
        return False

    def fade_to(self, index):
        if self.phase is not None:
            self.finish_now()
        self.pending = index
        self.clock.start()
        self.generation += 1
        if WEB:
            self.web_fade("out", FADE_OUT_MS)
            self.phase = "out"
            generation = self.generation
            QTimer.singleShot(FADE_OUT_MS, lambda: self.web_switch(generation))
            debug("web fade-out asked")
            return
        self.overlay.frames = 0
        self.overlay.setGeometry(self.stack.geometry())
        self.overlay.snapshot = self.stack.grab()
        debug("fade-out start: grab %d ms, overlay %s" % (self.clock.elapsed(), self.overlay.geometry()))
        self.overlay.set_cover(0.0)
        self.overlay.raise_()
        self.overlay.show()
        self.run("out", 0.0, 1.0, FADE_OUT_MS)

    def run(self, phase, start, end, ms):
        self.phase = phase
        self.animation.stop()
        self.animation.setDuration(ms)
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.start()

    def on_finished(self):
        if self.phase == "out":
            debug("fade-out done at %d ms, %d frames" % (self.clock.elapsed(), self.overlay.frames))
            index, self.pending = self.pending, None
            self.phase = "switching"
            self.overlay.snapshot = None        # plain background while the new page gets ready
            self.overlay.set_cover(1.0)
            self.tabs.setCurrentIndex(index)
            # the new page may build and lay itself out now (the first visit of an editor or picker tab);
            # start the fade-in clock only after that, or its first half would be skipped
            QTimer.singleShot(0, self.start_fade_in)
        elif self.phase == "in":
            debug("fade-in done at %d ms, %d frames in total" % (self.clock.elapsed(), self.overlay.frames))
            self.clear()

    def start_fade_in(self):
        if self.phase == "switching":
            self.overlay.setGeometry(self.stack.geometry())
            debug("new page ready at %d ms" % self.clock.elapsed())
            self.overlay.snapshot = self.stack.grab()      # the new page, laid out, as one picture
            debug("fade-in start at %d ms (after grab)" % self.clock.elapsed())
            self.run("in", 1.0, 0.0, FADE_IN_MS)

    # --- browser build: the page draws the fade

    def web_fade(self, phase, ms):
        import vialglue
        top_left = self.stack.mapToGlobal(self.stack.rect().topLeft())
        vialglue.fade(phase, top_left.x(), top_left.y(), self.stack.width(), self.stack.height(), ms)

    def web_switch(self, generation):
        if generation != self.generation or self.phase != "out":
            return
        index, self.pending = self.pending, None
        self.phase = "switching"
        self.tabs.setCurrentIndex(index)
        debug("web switched at %d ms" % self.clock.elapsed())
        QTimer.singleShot(0, lambda: self.web_fade_in(generation))

    def web_fade_in(self, generation):
        if generation != self.generation or self.phase != "switching":
            return
        self.stack.repaint()        # the new page onto the canvas before the cover lifts
        self.web_fade("in", FADE_IN_MS)
        self.phase = "in"
        debug("web fade-in asked at %d ms" % self.clock.elapsed())
        QTimer.singleShot(FADE_IN_MS, lambda: self.web_done(generation))

    def web_done(self, generation):
        if generation == self.generation and self.phase == "in":
            self.clear()

    def finish_now(self):
        """A second click while fading: land on the pending tab at once, then start over"""
        self.animation.stop()
        self.generation += 1
        if self.pending is not None:
            index, self.pending = self.pending, None
            self.tabs.setCurrentIndex(index)
        if WEB:
            self.web_fade("in", 0)
        self.clear()

    def clear(self):
        self.phase = None
        self.overlay.hide()
        self.overlay.snapshot = None

    def busy(self):
        return self.phase is not None


def fader(tabs):
    return tabs.findChild(TabFader, options=Qt.FindDirectChildrenOnly)


def is_enabled(tabs):
    return bool(tabs.property(PROPERTY))


def enable(tabs):
    if not is_enabled(tabs):
        TabFader(tabs)
        tabs.setProperty(PROPERTY, True)


def enable_all(root):
    for tabs in root.findChildren(QTabWidget):
        enable(tabs)
