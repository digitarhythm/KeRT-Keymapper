from collections import defaultdict

from PyQt5.QtGui import QPainter, QColor, QPainterPath, QTransform, QBrush, QPolygonF, QPalette, QPen
from PyQt5.QtWidgets import QWidget, QToolTip, QApplication
from PyQt5.QtCore import Qt, QSize, QRect, QPointF, pyqtSignal, QEvent, QRectF, QTimer, QElapsedTimer

from constants import KEY_SIZE_RATIO, KEY_SPACING_RATIO, KEYBOARD_WIDGET_PADDING, \
    KEYBOARD_WIDGET_MASK_HEIGHT, KEY_ROUNDNESS, SHADOW_SIDE_PADDING, SHADOW_TOP_PADDING, SHADOW_BOTTOM_PADDING, \
    KEYBOARD_WIDGET_NONMASK_PADDING
from themes import Theme
import key_style


# auto-fit never goes below this scale (a too small window scrolls/clips instead of vanishing keys)
MIN_FIT_SCALE = 0.3


class KeyWidget:

    def __init__(self, desc, scale, shift_x=0, shift_y=0):
        self.active = False
        self.on = False
        self.masked = False
        self.pressed = False
        self.desc = desc
        self.text = ""
        self.mask_text = ""
        self.tooltip = ""
        self.color = None
        self.mask_color = None
        self.scale = 0

        self.rotation_angle = desc.rotation_angle

        self.has2 = desc.width2 != desc.width or desc.height2 != desc.height or desc.x2 != 0 or desc.y2 != 0

        self.update_position(scale, shift_x, shift_y)

    def update_position(self, scale, shift_x=0, shift_y=0):
        if self.scale != scale or self.shift_x != shift_x or self.shift_y != shift_y:
            self.scale = scale
            self.size = self.scale * (KEY_SIZE_RATIO + KEY_SPACING_RATIO)
            spacing = self.scale * KEY_SPACING_RATIO

            self.rotation_x = self.size * self.desc.rotation_x
            self.rotation_y = self.size * self.desc.rotation_y

            self.shift_x = shift_x
            self.shift_y = shift_y
            self.x = self.size * self.desc.x
            self.y = self.size * self.desc.y
            self.w = self.size * self.desc.width - spacing
            self.h = self.size * self.desc.height - spacing

            self.rect = QRect(
                round(self.x),
                round(self.y),
                round(self.w),
                round(self.h)
            )
            self.text_rect = QRect(
                round(self.x),
                round(self.y + self.size * SHADOW_TOP_PADDING),
                round(self.w),
                round(self.h - self.size * (SHADOW_BOTTOM_PADDING + SHADOW_TOP_PADDING))
            )

            self.x2 = self.x + self.size * self.desc.x2
            self.y2 = self.y + self.size * self.desc.y2
            self.w2 = self.size * self.desc.width2 - spacing
            self.h2 = self.size * self.desc.height2 - spacing

            self.rect2 = QRect(
                round(self.x2),
                round(self.y2),
                round(self.w2),
                round(self.h2)
            )

            self.bbox = self.calculate_bbox(self.rect)
            self.bbox2 = self.calculate_bbox(self.rect2)
            self.polygon = QPolygonF(self.bbox + [self.bbox[0]])
            self.polygon2 = QPolygonF(self.bbox2 + [self.bbox2[0]])
            self.polygon = self.polygon.united(self.polygon2)
            self.corner = key_style.key_corner() if key_style.FLAT_KEYS else self.size * KEY_ROUNDNESS
            if key_style.FLAT_KEYS:
                self.text_rect = QRect(self.rect)
            self.background_draw_path = self.calculate_background_draw_path()
            self.foreground_draw_path = QPainterPath() if key_style.FLAT_KEYS else self.calculate_foreground_draw_path()
            self.extra_draw_path = self.calculate_extra_draw_path()

            # calculate areas where the inner keycode will be located
            # nonmask = outer (e.g. Rsft_T)
            # mask = inner (e.g. KC_A)
            self.nonmask_rect = QRect(
                round(self.x),
                round(self.y + self.size * KEYBOARD_WIDGET_NONMASK_PADDING),
                round(self.w),
                round(self.h * (1 - KEYBOARD_WIDGET_MASK_HEIGHT))
            )
            self.mask_rect = QRect(
                round(self.x + self.size * SHADOW_SIDE_PADDING),
                round(self.y + self.h * (1 - KEYBOARD_WIDGET_MASK_HEIGHT)),
                round(self.w - 2 * self.size * SHADOW_SIDE_PADDING),
                round(self.h * KEYBOARD_WIDGET_MASK_HEIGHT - self.size * SHADOW_BOTTOM_PADDING)
            )
            self.mask_bbox = self.calculate_bbox(self.mask_rect)
            self.mask_polygon = QPolygonF(self.mask_bbox + [self.mask_bbox[0]])

    def calculate_bbox(self, rect):
        x1 = rect.topLeft().x()
        y1 = rect.topLeft().y()
        x2 = rect.bottomRight().x()
        y2 = rect.bottomRight().y()
        points = [(x1, y1), (x1, y2), (x2, y2), (x2, y1)]
        bbox = []
        for p in points:
            t = QTransform()
            t.translate(self.shift_x, self.shift_y)
            t.translate(self.rotation_x, self.rotation_y)
            t.rotate(self.rotation_angle)
            t.translate(-self.rotation_x, -self.rotation_y)
            p = t.map(QPointF(p[0], p[1]))
            bbox.append(p)
        return bbox

    def calculate_background_draw_path(self):
        path = QPainterPath()
        path.addRoundedRect(
            round(self.x),
            round(self.y),
            round(self.w),
            round(self.h),
            self.corner,
            self.corner
        )

        # second part only considered if different from first
        if self.has2:
            path2 = QPainterPath()
            path2.addRoundedRect(
                round(self.x2),
                round(self.y2),
                round(self.w2),
                round(self.h2),
                self.corner,
                self.corner
            )
            path = path.united(path2)

        return path

    def calculate_foreground_draw_path(self):
        path = QPainterPath()
        path.addRoundedRect(
            round(self.x + self.size * SHADOW_SIDE_PADDING),
            round(self.y + self.size * SHADOW_TOP_PADDING),
            round(self.w - 2 * self.size * SHADOW_SIDE_PADDING),
            round(self.h - self.size * (SHADOW_BOTTOM_PADDING + SHADOW_TOP_PADDING)),
            self.corner,
            self.corner
        )

        # second part only considered if different from first
        if self.has2:
            path2 = QPainterPath()
            path2.addRoundedRect(
                round(self.x2 + self.size * SHADOW_SIDE_PADDING),
                round(self.y2 + self.size * SHADOW_TOP_PADDING),
                round(self.w2 - 2 * self.size * SHADOW_SIDE_PADDING),
                round(self.h2 - self.size * (SHADOW_BOTTOM_PADDING + SHADOW_TOP_PADDING)),
                self.corner,
                self.corner
            )
            path = path.united(path2)

        return path

    def calculate_extra_draw_path(self):
        return QPainterPath()

    def setText(self, text):
        self.text = text

    def setMaskText(self, text):
        self.mask_text = text

    def setToolTip(self, tooltip):
        self.tooltip = tooltip

    def setActive(self, active):
        self.active = active

    def setOn(self, on):
        self.on = on

    def setPressed(self, pressed):
        self.pressed = pressed

    def setColor(self, color):
        self.color = color

    def setMaskColor(self, color):
        self.mask_color = color

    def __repr__(self):
        qualifiers = ["KeyboardWidget"]
        if self.desc.row is not None:
            qualifiers.append("matrix:{},{}".format(self.desc.row, self.desc.col))
        if self.desc.layout_index != -1:
            qualifiers.append("layout:{},{}".format(self.desc.layout_index, self.desc.layout_option))
        return " ".join(qualifiers)


class EncoderWidget(KeyWidget):

    def calculate_background_draw_path(self):
        path = QPainterPath()
        path.addEllipse(round(self.x), round(self.y), round(self.w), round(self.h))
        return path

    def calculate_foreground_draw_path(self):
        path = QPainterPath()
        path.addEllipse(
            round(self.x + self.size * SHADOW_SIDE_PADDING),
            round(self.y + self.size * SHADOW_TOP_PADDING),
            round(self.w - 2 * self.size * SHADOW_SIDE_PADDING),
            round(self.h - self.size * (SHADOW_BOTTOM_PADDING + SHADOW_TOP_PADDING))
        )
        return path

    def calculate_extra_draw_path(self):
        path = QPainterPath()
        # midpoint of arrow triangle
        p = self.h
        x = self.x
        y = self.y + p / 2
        if self.desc.encoder_dir == 0:
            # counterclockwise - pointing down
            path.moveTo(round(x), round(y))
            path.lineTo(round(x + p / 10), round(y - p / 10))
            path.lineTo(round(x), round(y + p / 10))
            path.lineTo(round(x - p / 10), round(y - p / 10))
            path.lineTo(round(x), round(y))
        else:
            # clockwise - pointing up
            path.moveTo(round(x), round(y))
            path.lineTo(round(x + p / 10), round(y + p / 10))
            path.lineTo(round(x), round(y - p / 10))
            path.lineTo(round(x - p / 10), round(y + p / 10))
            path.lineTo(round(x), round(y))
        return path

    def __repr__(self):
        return "EncoderWidget"


class KeyboardWidget(QWidget):

    clicked = pyqtSignal()
    deselected = pyqtSignal()
    anykey = pyqtSignal()

    def __init__(self, layout_editor):
        super().__init__()

        self.enabled = True
        self.scale = 1
        self.padding = KEYBOARD_WIDGET_PADDING

        self.setMouseTracking(True)
        # hover_zoom: grow the key under the mouse by key_style.HOVER_GROW_PX on every side, with a white frame,
        # growing and shrinking over HOVER_ANIM_MS (the keymap turns it on)
        self.hover_zoom = False
        self.hover_key = None
        self.after_paint = None             # called once after the next paint
        self.zoom = {}              # key -> progress 0..1 of its zoom (only keys that are zoomed at all)
        self._laid_out_for = None   # (scale, padding) of the last update_layout()
        self.zoom_timer = QTimer(self)
        self.zoom_timer.setInterval(16)
        self.zoom_timer.timeout.connect(self.step_zoom)
        self.zoom_clock = QElapsedTimer()

        self.layout_editor = layout_editor

        # widgets common for all layouts
        self.common_widgets = []

        # layout-specific widgets
        self.widgets_for_layout = []

        # widgets in current layout
        self.widgets = []

        self.width = self.height = 0
        self.active_key = None
        self.active_mask = False
        # fit mode (KeymapEditor auto-fit): the layout may give this widget less than its size hint,
        # the editor then rescales the keys to what it got instead of forcing the window to grow
        self.fit_mode = False

    def set_keys(self, keys, encoders):
        self.common_widgets = []
        self.widgets_for_layout = []

        self.add_keys([(x, KeyWidget) for x in keys] + [(x, EncoderWidget) for x in encoders])
        self.update_layout()

    def add_keys(self, keys):
        scale_factor = self.fontMetrics().height()

        for key, cls in keys:
            if key.layout_index == -1:
                self.common_widgets.append(cls(key, scale_factor))
            else:
                self.widgets_for_layout.append(cls(key, scale_factor))

    def place_widgets(self):
        scale_factor = self.fontMetrics().height()

        self.widgets = []

        # place common widgets, that is, ones which are always displayed and require no extra transforms
        for widget in self.common_widgets:
            widget.update_position(scale_factor)
            self.widgets.append(widget)

        # top-left position for specific layout
        layout_x = defaultdict(lambda: defaultdict(lambda: 1e6))
        layout_y = defaultdict(lambda: defaultdict(lambda: 1e6))

        # determine top-left position for every layout option
        for widget in self.widgets_for_layout:
            widget.update_position(scale_factor)
            idx, opt = widget.desc.layout_index, widget.desc.layout_option
            p = widget.polygon.boundingRect().topLeft()
            layout_x[idx][opt] = min(layout_x[idx][opt], p.x())
            layout_y[idx][opt] = min(layout_y[idx][opt], p.y())

        # obtain widgets for all layout options now that we know how to shift them
        for widget in self.widgets_for_layout:
            idx, opt = widget.desc.layout_index, widget.desc.layout_option
            if opt == self.layout_editor.get_choice(idx):
                shift_x = layout_x[idx][opt] - layout_x[idx][0]
                shift_y = layout_y[idx][opt] - layout_y[idx][0]
                widget.update_position(scale_factor, -shift_x, -shift_y)
                self.widgets.append(widget)

        # at this point some widgets on left side might be cutoff, or there may be too much empty space
        # calculate top left position of visible widgets and shift everything around
        top_x = top_y = 1e6
        for widget in self.widgets:
            if not widget.desc.decal:
                p = widget.polygon.boundingRect().topLeft()
                top_x = min(top_x, p.x())
                top_y = min(top_y, p.y())
        for widget in self.widgets:
            widget.update_position(widget.scale, widget.shift_x - top_x + self.padding,
                                   widget.shift_y - top_y + self.padding)

    def update_layout(self):
        """ Updates self.widgets for the currently active layout """
        self._laid_out_for = (self.scale, self.padding)

        # determine widgets for current layout
        self.place_widgets()
        self.widgets = list(filter(lambda w: not w.desc.decal, self.widgets))

        self.widgets.sort(key=lambda w: (w.y, w.x))

        # determine maximum width and height of container
        max_w = max_h = 0
        for key in self.widgets:
            p = key.polygon.boundingRect().bottomRight()
            max_w = max(max_w, p.x() * self.scale)
            max_h = max(max_h, p.y() * self.scale)

        size = (round(max_w + 2 * self.padding), round(max_h + 2 * self.padding))
        resized = size != (self.width, self.height)
        self.width, self.height = size

        self.update()
        # only when the size changed: updateGeometry() runs the layouts up to the main window, which then
        # repaints everything (a layer switch repainted the whole window, ~120 ms in the browser)
        if resized:
            self.updateGeometry()

    def paintEvent(self, event):
        self._paint(event)
        if self.after_paint is not None:
            # once, right after this paint (KeymapEditor.switch_layer: the layer highlight's slide)
            callback, self.after_paint = self.after_paint, None
            QTimer.singleShot(0, callback)

    def _paint(self, event):
        qp = QPainter()
        qp.begin(self)
        qp.setRenderHint(QPainter.Antialiasing)

        # for regular keycaps
        regular_pen = qp.pen()
        regular_pen.setColor(QApplication.palette().color(QPalette.ButtonText))
        qp.setPen(regular_pen)

        background_brush = QBrush()
        background_brush.setColor(QApplication.palette().color(QPalette.Button))
        background_brush.setStyle(Qt.SolidPattern)

        foreground_brush = QBrush()
        foreground_brush.setColor(QApplication.palette().color(QPalette.Button).lighter(120))
        foreground_brush.setStyle(Qt.SolidPattern)

        mask_brush = QBrush()
        mask_brush.setColor(QApplication.palette().color(QPalette.Button).lighter(Theme.mask_light_factor()))
        mask_brush.setStyle(Qt.SolidPattern)

        # for currently selected keycap
        active_pen = qp.pen()
        active_pen.setColor(QApplication.palette().color(QPalette.Highlight))
        active_pen.setWidthF(1.5)

        # flat keys get a thin outline so a white key stands out on a light background
        outline_pen = qp.pen()
        outline_pen.setColor(QApplication.palette().color(QPalette.Mid))
        outline_pen.setWidthF(key_style.OUTLINE_WIDTH)
        inactive_pen = outline_pen if key_style.FLAT_KEYS else Qt.NoPen

        # for the encoder arrow
        extra_pen = regular_pen
        extra_brush = QBrush()
        extra_brush.setColor(QApplication.palette().color(QPalette.ButtonText))
        extra_brush.setStyle(Qt.SolidPattern)

        # for pressed keycaps
        background_pressed_brush = QBrush()
        background_pressed_brush.setColor(QApplication.palette().color(QPalette.Highlight))
        background_pressed_brush.setStyle(Qt.SolidPattern)

        foreground_pressed_brush = QBrush()
        foreground_pressed_brush.setColor(QApplication.palette().color(QPalette.Highlight).lighter(120))
        foreground_pressed_brush.setStyle(Qt.SolidPattern)

        background_on_brush = QBrush()
        background_on_brush.setColor(QApplication.palette().color(QPalette.Highlight).darker(150))
        background_on_brush.setStyle(Qt.SolidPattern)

        foreground_on_brush = QBrush()
        foreground_on_brush.setColor(QApplication.palette().color(QPalette.Highlight).darker(120))
        foreground_on_brush.setStyle(Qt.SolidPattern)

        # flat keys: the selected key is filled with the highlight colour and its legend inverted
        selected_brush = QBrush()
        selected_brush.setColor(QApplication.palette().color(QPalette.Highlight))
        selected_brush.setStyle(Qt.SolidPattern)
        selected_text_pen = qp.pen()
        selected_text_pen.setColor(QApplication.palette().color(QPalette.HighlightedText))

        mask_font = qp.font()
        mask_font.setPointSize(round(mask_font.pointSize() * 0.8))

        # dark key look (key_style.DARK_KEYS): black face, white legend, no outline, soft drop shadow
        dark = key_style.FLAT_KEYS and key_style.DARK_KEYS
        if dark:
            regular_pen.setColor(QColor(key_style.KEY_LEGEND))
            background_brush.setColor(key_style.face_color())
            mask_brush.setColor(QColor(key_style.KEY_MASK_FACE))
            extra_brush.setColor(QColor(key_style.KEY_LEGEND))
            inactive_pen = Qt.NoPen
            # every shadow first, so no key's shadow is drawn over its neighbour; but the hovered key's, drawn
            # with it on top of its neighbours
            for key in self.paint_order(event.rect()):
                if key is self.hover_key and self.hover_zoom:
                    continue
                qp.save()
                self.key_transform(qp, key)
                key_style.paint_shadow(qp, lambda p, k=key: p.drawPath(k.background_draw_path),
                                       unit=1.0 / self.scale if self.scale else 1.0)
                qp.restore()

        for key in self.paint_order(event.rect()):
            qp.save()
            self.key_transform(qp, key)
            if dark and key is self.hover_key and self.hover_zoom:
                key_style.paint_shadow(qp, lambda p, k=key: p.drawPath(k.background_draw_path),
                                       unit=1.0 / self.scale if self.scale else 1.0)

            active = key.active or (self.active_key == key and not self.active_mask)

            # draw keycap background/drop-shadow (or the whole flat key); a selected flat key keeps its dark
            # outline, only the fill shows the (light grey) highlight
            qp.setPen(active_pen if active and not key_style.FLAT_KEYS else inactive_pen)
            brush = background_brush
            if key.pressed:
                brush = background_pressed_brush
            elif key.on:
                brush = background_on_brush
            elif active and key_style.FLAT_KEYS:
                brush = selected_brush
            if dark and key is self.hover_key and self.hover_zoom:
                # the faces are translucent: an opaque backdrop in the page colour first, so the neighbours
                # under the grown key do not show through it and it reads as the top one
                qp.setBrush(self.palette().color(QPalette.Window))
                qp.drawPath(key.background_draw_path)
            qp.setBrush(brush)
            qp.drawPath(key.background_draw_path)
            legend_pen = selected_text_pen if (active and key_style.FLAT_KEYS and not key.pressed and not key.on) \
                else regular_pen
            legend_colour = key.color

            # draw keycap foreground
            qp.setPen(Qt.NoPen)
            brush = foreground_brush
            if key.pressed:
                brush = foreground_pressed_brush
            elif key.on:
                brush = foreground_on_brush
            qp.setBrush(brush)
            qp.drawPath(key.foreground_draw_path)

            # draw key text
            if key.masked:
                # draw the outer legend
                qp.setFont(mask_font)
                qp.setPen(legend_colour if legend_colour else legend_pen)
                qp.drawText(key.nonmask_rect, Qt.AlignCenter, key.text)

                # draw the inner highlight rect
                qp.setPen(active_pen if self.active_key == key and self.active_mask else inactive_pen)
                qp.setBrush(mask_brush)
                mask_corner = key.corner * 0.6 if key_style.FLAT_KEYS else key.corner
                qp.drawRoundedRect(key.mask_rect, mask_corner, mask_corner)

                # draw the inner legend
                qp.setPen(key.mask_color if key.mask_color else regular_pen)
                qp.drawText(key.mask_rect, Qt.AlignCenter, key.mask_text)
            else:
                # draw the legend
                qp.setPen(legend_colour if legend_colour else legend_pen)
                qp.drawText(key.text_rect, Qt.AlignCenter, key.text)

            # draw the extra shape (encoder arrow)
            qp.setPen(extra_pen)
            qp.setBrush(extra_brush)
            qp.drawPath(key.extra_draw_path)

            qp.restore()

            # the selected key's orange frame, else the hovered key's white one fading in with the zoom
            # (keymap only)
            if self.hover_zoom and key is self.active_key:
                self.paint_select_frame(qp, key)
            elif self.hover_zoom and self.zoom.get(key, 0.0) > 0.0:
                self.paint_select_frame(qp, key, key_style.HOVER_RING_COLOR, self.zoom_eased(key))

        qp.end()

    def sizeHint(self):
        return QSize(self.width, self.height)

    def minimumSizeHint(self):
        if self.fit_mode:
            return QSize(0, 0)
        return QSize(self.width, self.height)

    def content_size(self):
        """(width, height) of the key area at scale 1, without padding"""
        max_w = max_h = 0
        for key in self.widgets:
            p = key.polygon.boundingRect().bottomRight()
            max_w = max(max_w, p.x())
            max_h = max(max_h, p.y())
        return max_w, max_h

    def fit_scale(self, width, height, max_scale=None):
        """Largest scale at which every key (plus padding) fits into width x height; None without keys"""
        w, h = self.content_size()
        if w <= 0 or h <= 0:
            return None
        scale = min((width - 2 * self.padding) / w, (height - 2 * self.padding) / h)
        if max_scale is not None:
            scale = min(scale, max_scale)
        return max(scale, MIN_FIT_SCALE)

    def hit_test(self, pos):
        """ Returns key, hit_masked_part """

        for key in self.widgets:
            if key.masked and key.mask_polygon.containsPoint(pos/self.scale, Qt.OddEvenFill):
                return key, True
            if key.polygon.containsPoint(pos/self.scale, Qt.OddEvenFill):
                return key, False

        return None, False

    def paint_order(self, area=None):
        """Keys to draw: those touching `area` (the region being repainted; None = all); the selected key
        (its frame) and then the zoomed ones last, the most zoomed on top, so they cover their neighbours;
        the key under the mouse is always the very last, also while the key it left is still bigger"""
        keys = self.widgets
        if area is not None:
            keys = [k for k in keys if self.key_screen_rect(k).intersects(area)]
        rank = lambda k: (k is self.hover_key, self.zoom.get(k, 0.0), k is self.active_key)
        if not any(rank(k) != (False, 0.0, False) for k in keys):
            return keys
        return sorted(keys, key=rank)

    def key_screen_rect(self, key):
        """Where a key can paint on screen, with room for its zoom, frame and shadow"""
        r = key.polygon.boundingRect()
        margin = key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH \
            + key_style.SHADOW_OFFSET + key_style.SHADOW_BLUR + 2
        return QRectF(r.left() * self.scale, r.top() * self.scale, r.width() * self.scale,
                      r.height() * self.scale).adjusted(-margin, -margin, margin, margin).toAlignedRect()

    def zoom_progress(self, key):
        return self.zoom.get(key, 0.0)

    def zoom_eased(self, key):
        """0..1 with ease-in-out (smoothstep) of the key's zoom progress"""
        t = self.zoom.get(key, 0.0)
        return t * t * (3 - 2 * t)

    def zoom_grow(self, key):
        """How far the key has grown on each side, in key coordinates"""
        return key_style.HOVER_GROW_PX * self.zoom_eased(key) / (self.scale or 1.0)

    def enable_hover_zoom(self):
        """Grow the key under the mouse; leave room around the keys for the grown key and its frame"""
        self.hover_zoom = True
        self.padding = KEYBOARD_WIDGET_PADDING + key_style.HOVER_GROW_PX + key_style.HOVER_FRAME_GAP \
            + key_style.HOVER_FRAME_WIDTH
        self.update_layout()

    def step_zoom(self):
        """One animation frame: move every zoomed key toward its target (1 under the mouse, 0 elsewhere)
        and repaint only the area those keys cover"""
        if key_style.HOVER_ANIM_MS <= 0:
            step = 1.0
        else:
            step = self.zoom_clock.restart() / max(1, key_style.HOVER_ANIM_MS)
        dirty = QRect()
        for key in list(self.zoom):
            if key not in self.widgets:
                del self.zoom[key]
                continue
            target = 1.0 if key is self.hover_key else 0.0
            p = self.zoom[key]
            p = min(target, p + step) if target > p else max(target, p - step)
            dirty = dirty.united(self.key_screen_rect(key))
            if p <= 0.0 and target == 0.0:
                del self.zoom[key]
            else:
                self.zoom[key] = p
        if all(self.zoom[k] == (1.0 if k is self.hover_key else 0.0) for k in self.zoom):
            self.zoom_timer.stop()
        if not dirty.isEmpty():
            self.update(dirty)

    def paint_select_frame(self, qp, key, colour=key_style.HOVER_FRAME_COLOR, opacity=1.0):
        """Rounded frame just outside a key, around its grown size when the mouse is on it: orange for the
        selected (clicked) key, white (key_style.HOVER_RING_COLOR, fading with the zoom) for the hovered one"""
        # drawn without the zoom's stretch, so the frame is evenly HOVER_FRAME_WIDTH thick with round corners
        unit = 1.0 / self.scale if self.scale else 1.0
        c = QColor(colour)
        c.setAlphaF(max(0.0, min(1.0, opacity)))
        pen = QPen(c, key_style.HOVER_FRAME_WIDTH * unit)
        out = self.zoom_grow(key) + (key_style.HOVER_FRAME_GAP + key_style.HOVER_FRAME_WIDTH / 2) * unit
        radius = key_style.HOVER_FRAME_RADIUS * unit
        qp.save()
        self.key_transform(qp, key, zoomed=False)
        qp.setPen(pen)
        qp.setBrush(Qt.NoBrush)
        qp.drawRoundedRect(key.background_draw_path.boundingRect().adjusted(-out, -out, out, out), radius, radius)
        qp.restore()

    def key_transform(self, qp, key, zoomed=True):
        """Painter transform for one key: widget scale, the key's place and rotation, and (zoomed) the hover
        zoom around the key's own centre: HOVER_GROW_PX more on every side"""
        qp.scale(self.scale, self.scale)
        qp.translate(key.shift_x, key.shift_y)
        qp.translate(key.rotation_x, key.rotation_y)
        qp.rotate(key.rotation_angle)
        qp.translate(-key.rotation_x, -key.rotation_y)
        if zoomed and self.zoom.get(key, 0.0) > 0.0:
            r = key.background_draw_path.boundingRect()
            if r.width() > 0 and r.height() > 0:
                g = self.zoom_grow(key)
                centre = r.center()
                qp.translate(centre)
                qp.scale((r.width() + 2 * g) / r.width(), (r.height() + 2 * g) / r.height())
                qp.translate(-centre)

    def set_hover(self, key):
        if key is self.hover_key:
            return
        self.hover_key = key
        if key is not None:
            self.zoom.setdefault(key, 0.0)
        if key_style.HOVER_ANIM_MS <= 0:
            self.step_zoom()             # no animation: one step to the end, no timer
            return
        if not self.zoom_timer.isActive():
            self.zoom_clock.start()
            self.zoom_timer.start()
        self.step_zoom()

    def mousePressEvent(self, ev):
        if not self.enabled:
            return

        self.active_key, self.active_mask = self.hit_test(ev.pos())
        if self.active_key is not None:
            self.clicked.emit()
        else:
            self.deselected.emit()
        self.update()

    def resizeEvent(self, ev):
        # the keys' positions depend on the scale and the padding, not on the widget's size: a resize
        # (there are many while the window comes up) only needs a new layout when those changed since.
        # Layer, layout-option and zoom changes lay the keys out themselves.
        if self.isEnabled() and self._laid_out_for != (self.scale, self.padding):
            self.update_layout()

    def select_next(self):
        """ Selects next key based on their order in the keymap """

        keys_looped = self.widgets + [self.widgets[0]]
        for x, key in enumerate(keys_looped):
            if key == self.active_key:
                self.active_key = keys_looped[x + 1]
                self.active_mask = False
                self.clicked.emit()
                return

    def deselect(self):
        if self.active_key is not None:
            self.active_key = None
            self.deselected.emit()
            self.update()

    def event(self, ev):
        if not self.enabled:
            super().event(ev)

        if ev.type() == QEvent.ToolTip:
            key = self.hit_test(ev.pos())[0]
            if key is not None:
                QToolTip.showText(ev.globalPos(), key.tooltip)
            else:
                QToolTip.hideText()
        elif ev.type() == QEvent.LayoutRequest:
            self.update_layout()
        elif ev.type() == QEvent.MouseMove and self.hover_zoom:
            self.set_hover(self.hit_test(ev.pos())[0] if self.enabled else None)
        elif ev.type() == QEvent.Leave and self.hover_zoom:
            self.set_hover(None)
        elif ev.type() == QEvent.MouseButtonDblClick and self.active_key:
            self.anykey.emit()
        return super().event(ev)

    def set_enabled(self, val):
        self.enabled = val

    def set_scale(self, scale):
        self.scale = scale

    def get_scale(self):
        return self.scale
