# SPDX-License-Identifier: GPL-2.0-or-later
"""Drop shadows under the tabs in the dark key look (key_style.DARK_KEYS, docs/dark-keys-spec.md).

A stylesheet cannot draw shadows, so every tab bar gets an event filter that paints the shadows of its
tabs just before the tab bar paints itself; the stylesheet keeps KEY_MARGINS free inside each tab for
them (QTabBar::tab { margin }), and the tabs' faces are then drawn on top.
"""
from PyQt5.QtCore import QEvent, QObject, QRectF
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QPushButton, QTabBar

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


# ---- key buttons (picker keys, display keyboards, zoom buttons): shadows painted by their parent

PARENT_PROPERTY = "keyShadowParent"


class KeyButtonShadows(QObject):
    """On the parent's paint event (the parent paints before its children): the shadows of the key
    buttons inside the area being repainted, under their faces"""

    def eventFilter(self, parent, ev):
        if ev.type() == QEvent.Paint and key_style.DARK_KEYS:
            area = QRectF(ev.rect())
            left, top, right, bottom = key_style.KEY_MARGINS
            r = key_style.KEY_RADIUS
            p = None
            for child in parent.children():
                if not isinstance(child, QPushButton) or not child.property("keyButton") or not child.isVisible():
                    continue
                face = QRectF(child.geometry()).adjusted(left, top, -right, -bottom)
                if not face.adjusted(-8, -8, 8, 8).intersects(area):
                    continue
                if p is None:
                    p = QPainter(parent)
                    p.setRenderHint(QPainter.Antialiasing)
                key_style.paint_shadow(p, lambda painter, f=face: painter.drawRoundedRect(f, r, r))
            if p is not None:
                p.end()
        return False


_button_filter = None


def install_parent(widget):
    """Let `widget` paint the shadows of the key buttons it holds (once)"""
    global _button_filter
    if widget is None or widget.property(PARENT_PROPERTY):
        return
    if _button_filter is None:
        _button_filter = KeyButtonShadows()
    widget.installEventFilter(_button_filter)
    widget.setProperty(PARENT_PROPERTY, True)
