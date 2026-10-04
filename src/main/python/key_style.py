# SPDX-License-Identifier: GPL-2.0-or-later
"""How keys are drawn (see docs/theme-flat-keys-spec.md).

FLAT_KEYS = True  : one flat rounded rectangle with an outline, legend centred (this fork's look)
FLAT_KEYS = False : upstream's keycap look (drop shadow + lighter top face)
"""

FLAT_KEYS = True

# corner radius of a flat key, in key coordinates (= pixels at drawing scale 1.0)
CORNER_RADIUS = 10

# outline width of a flat key (and of every other box in the KeRT Color theme), in pixels
OUTLINE_WIDTH = 3

# ---- dark key look (2026-09-29 trial, docs/dark-keys-spec.md) ----
# DARK_KEYS = True : black face, white legend, no outline, KEY_RADIUS corners, soft black drop shadow,
#                    on the keymap and on the picker key buttons.
# DARK_KEYS = False: the white face with a OUTLINE_WIDTH outline and CORNER_RADIUS corners (before).
DARK_KEYS = True

# silver faces with dark legends (2026-10-04; #f0f0f0, peach, white, pastel green and black before)
KEY_FACE = "#c0c0c0"
KEY_LEGEND = "#1f2328"
KEY_RADIUS = 8
KEY_HOVER_FACE = "#b0b0b0"      # tab / keyboard selector under the mouse: a slightly darker grey
KEY_MASK_FACE = "#d4d4d4"       # inner box of a mod-tap / layer-tap key (LT(1, KC_A) ...): a lighter grey
KEY_OVERRIDE_LEGEND = "#0a3069" # a remapped legend (Colemak ...); the palette's Link blue is too light
# the faces (KEY_FACE, KEY_HOVER_FACE) are drawn at this opacity, the legends stay solid (0.8 in the 2026-10-04
# trial, opaque again since); paint_shadow() leaves the face's own area out, so the shadow never shows through
KEY_FACE_OPACITY = 1.0


def face_color(name=None):
    """A face colour (KEY_FACE by default) with KEY_FACE_OPACITY"""
    from PyQt5.QtGui import QColor
    c = QColor(name or KEY_FACE)
    c.setAlpha(round(255 * KEY_FACE_OPACITY))
    return c


def face_css(name=None):
    """The same for stylesheets: rgba(r, g, b, alpha 0..255)"""
    c = face_color(name)
    return "rgba({}, {}, {}, {})".format(c.red(), c.green(), c.blue(), c.alpha())

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


class _ShapeRecorder:
    """Stands in for a QPainter to collect what a paint_shadow() `draw` function draws as a path"""

    def __init__(self):
        from PyQt5.QtGui import QPainterPath
        self.path = QPainterPath()

    def drawRoundedRect(self, rect, rx, ry, *args):
        self.path.addRoundedRect(rect, rx, ry)

    def drawPath(self, path):
        self.path.addPath(path)


def paint_shadow(painter, draw, unit=1.0, exclude=None):
    """Soft black shadow of a shape: `draw(painter)` draws the shape's outline path/rect; it is drawn
    SHADOW_BLUR times, each with a wider translucent pen, SHADOW_OFFSET down. `unit` is the size of one
    screen pixel in the painter's coordinates (1 / scale when the painter is scaled). The shape itself is
    left out (but for a 1 px rim under its antialiased edge), as the face drawn over it is translucent;
    `exclude` (a path) leaves out more faces instead, e.g. all the neighbours drawn over the shadow."""
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QColor, QPainterPath, QPainterPathStroker, QPen
    painter.save()
    shape = _ShapeRecorder()
    if KEY_FACE_OPACITY < 1.0:
        draw(shape)                  # opaque faces cover their shadow anyway: no (slow) cut-out
    if not shape.path.isEmpty():
        # clip: around the shape, minus the shape shrunk by a 1 px rim
        area = exclude if exclude is not None else shape.path
        rim = QPainterPathStroker()
        rim.setWidth(2 * unit)
        inner = area.subtracted(rim.createStroke(area))
        margin = (SHADOW_OFFSET + SHADOW_BLUR + 4) * unit
        outer = QPainterPath()
        outer.addRect(shape.path.boundingRect().adjusted(-margin, -margin, margin, margin))
        painter.setClipPath(outer.subtracted(inner), Qt.IntersectClip)
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
# 0 = no animation: the key jumps to its grown size and back (2026-10-04 trial, 120 before: it felt heavy in
# the browser)
HOVER_ANIM_MS = 0
HOVER_FRAME_COLOR = "#ff8c00"
HOVER_FRAME_RADIUS = 10
HOVER_FRAME_WIDTH = 3
HOVER_FRAME_GAP = 2
# a hovered key (and layer button) keeps its face and legend colours and gets a frame of the same shape as
# the selected key's orange one; the orange frame wins on the selected key (2026-10-03; replaces the white
# face of 2026-10-02)
HOVER_RING_COLOR = "#000000"          # black (2026-10-04; white before)
