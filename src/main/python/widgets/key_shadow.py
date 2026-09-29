# SPDX-License-Identifier: GPL-2.0-or-later
"""Drop shadows under the tabs in the dark key look (key_style.DARK_KEYS, docs/dark-keys-spec.md).

A stylesheet cannot draw shadows, so every tab bar gets an event filter that paints the shadows of its
tabs just before the tab bar paints itself; the stylesheet keeps KEY_MARGINS free inside each tab for
them (QTabBar::tab { margin }), and the tabs' faces are then drawn on top.
"""
from PyQt5.QtCore import QEvent, QObject, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QTabBar

import key_style

PROPERTY = "keyShadow"


class TabShadow(QObject):

    def eventFilter(self, bar, ev):
        if ev.type() == QEvent.Paint and key_style.DARK_KEYS and isinstance(bar, QTabBar):
            left, top, right, bottom = key_style.KEY_MARGINS
            r = key_style.KEY_RADIUS
            p = QPainter(bar)
            p.setRenderHint(QPainter.Antialiasing)
            for i in range(bar.count()):
                face = QRectF(bar.tabRect(i)).adjusted(left, top, -right, -bottom)
                key_style.paint_shadow(p, lambda painter, f=face: painter.drawRoundedRect(f, r, r))
            p.end()
        return False


_filter = None


def install_all(root):
    """Give every tab bar under `root` the tab shadows (once)"""
    global _filter
    if _filter is None:
        _filter = TabShadow()
    for bar in root.findChildren(QTabBar):
        if not bar.property(PROPERTY):
            bar.installEventFilter(_filter)
            bar.setProperty(PROPERTY, True)
