# SPDX-License-Identifier: GPL-2.0-or-later
"""How keys are drawn (see docs/theme-flat-keys-spec.md).

FLAT_KEYS = True  : one flat rounded rectangle with an outline, legend centred (this fork's look)
FLAT_KEYS = False : upstream's keycap look (drop shadow + lighter top face)
"""

FLAT_KEYS = True

# corner radius of a flat key, in key coordinates (= pixels at drawing scale 1.0)
CORNER_RADIUS = 10

# outline width of a flat key (and of every other box in the KeRT Light theme), in pixels
OUTLINE_WIDTH = 3

# ---- dark key look (2026-09-29 trial, docs/dark-keys-spec.md) ----
# DARK_KEYS = True : black face, white legend, no outline, KEY_RADIUS corners, soft black drop shadow,
#                    on the keymap and on the picker key buttons.
# DARK_KEYS = False: the white face with a OUTLINE_WIDTH outline and CORNER_RADIUS corners (before).
DARK_KEYS = True

KEY_FACE = "#000000"
KEY_LEGEND = "#ffffff"
KEY_RADIUS = 8
KEY_HOVER_FACE = "#333333"      # picker key under the mouse
KEY_MASK_FACE = "#3a3a3a"       # inner box of a mod-tap / layer-tap key (LT(1, KC_A) ...)
KEY_OVERRIDE_LEGEND = "#79c0ff" # a remapped legend (Colemak ...); the palette's Link blue is unreadable on black

# drop shadow: SHADOW_OFFSET px down, softened over SHADOW_BLUR px, SHADOW_ALPHA per layer (out of 255)
SHADOW_OFFSET = 2
SHADOW_BLUR = 3
SHADOW_ALPHA = 45

# picker key buttons: the stylesheet margin (left, top, right, bottom) that leaves room for the shadow
# inside the button; together as wide as the old outline (2 * OUTLINE_WIDTH each way)
KEY_MARGINS = (3, 1, 3, 5)


def key_corner():
    return KEY_RADIUS if DARK_KEYS else CORNER_RADIUS


def override_color():
    from PyQt5.QtGui import QColor, QPalette
    from PyQt5.QtWidgets import QApplication
    if DARK_KEYS:
        return QColor(KEY_OVERRIDE_LEGEND)
    return QApplication.palette().color(QPalette.Link)


def paint_shadow(painter, draw, unit=1.0):
    """Soft black shadow of a shape: `draw(painter)` draws the shape's outline path/rect; it is drawn
    SHADOW_BLUR times, each with a wider translucent pen, SHADOW_OFFSET down. `unit` is the size of one
    screen pixel in the painter's coordinates (1 / scale when the painter is scaled)."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QPen
    painter.save()
    painter.translate(0, SHADOW_OFFSET * unit)
    colour = QColor(0, 0, 0, SHADOW_ALPHA)
    for i in range(SHADOW_BLUR, 0, -1):
        pen = QPen(colour, 2 * i * unit)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(colour)
        draw(painter)
    painter.restore()

# keymap: the key under the mouse grows by HOVER_GROW_PX on every side (screen pixels), on top of its
# neighbours (2026-10-01; 2026-10-02 a fixed growth instead of 1.08x: wide keys grew far sideways and
# keys at the edges pushed their frame out of the widget)
HOVER_GROW_PX = 5
# the hover zoom grows and shrinks over HOVER_ANIM_MS (ease in-out); an orange frame with HOVER_FRAME_RADIUS
# corners, HOVER_FRAME_WIDTH thick and HOVER_FRAME_GAP outside the key, fades in with it (2026-10-02)
HOVER_ANIM_MS = 120
HOVER_FRAME_COLOR = "#ff8c00"
HOVER_FRAME_RADIUS = 10
HOVER_FRAME_WIDTH = 3
HOVER_FRAME_GAP = 2
# while hovered (and growing) a key turns white with a black legend, fading with the zoom (2026-10-02);
# a remapped legend's light blue is unreadable on white, so it turns dark blue then
HOVER_FACE = "#ffffff"
HOVER_LEGEND = "#000000"
HOVER_OVERRIDE_LEGEND = "#0969da"


def mix(a, b, t):
    """Colour t of the way from a to b (0..1)"""
    from PyQt5.QtGui import QColor
    a, b = QColor(a), QColor(b)
    return QColor(round(a.red() + (b.red() - a.red()) * t), round(a.green() + (b.green() - a.green()) * t),
                  round(a.blue() + (b.blue() - a.blue()) * t))
