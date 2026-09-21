# SPDX-License-Identifier: GPL-2.0-or-later
"""Keyboard selector that shows each device on two lines: the owner (manufacturer) in a half-size font above
the keyboard name (docs/theme-flat-keys-spec.md §4.2.1)."""
from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QFont, QFontMetrics, QIcon, QPalette
from PyQt5.QtWidgets import QComboBox, QStyle, QStyledItemDelegate, QStyleOptionComboBox, QStylePainter

from branding_theme import COMBOBOX_PADDING_LEFT
from key_style import OUTLINE_WIDTH

ARROW_FALLBACK_WIDTH = 24
FRAME = OUTLINE_WIDTH
OWNER_MIN_POINT_SIZE = 6
OWNER_POINT_DELTA = 2      # owner line: half the selector's font size, plus this


def split_title(dev):
    """(owner, name) for a device: the manufacturer, and the rest of dev.title() (product name and suffix)."""
    title = dev.title()
    owner = (dev.desc.get("manufacturer_string") or "").strip() if hasattr(dev, "desc") else ""
    if owner and title.startswith(owner) and len(title) > len(owner):
        return owner, title[len(owner):].strip()
    return "", title


def owner_font_for(font):
    f = QFont(font)
    f.setPointSize(max(OWNER_MIN_POINT_SIZE, round(font.pointSize() / 2) + OWNER_POINT_DELTA))
    return f


def two_line_layout(area, owner, owner_font, name_font):
    """(owner_rect or None, name_rect) inside `area`; both lines centred vertically as a block."""
    ho = QFontMetrics(owner_font).height()
    hn = QFontMetrics(name_font).height()
    if not owner:
        top = area.top() + (area.height() - hn) // 2
        return None, QRect(area.left(), top, area.width(), hn)
    top = area.top() + (area.height() - ho - hn) // 2
    return (QRect(area.left(), top, area.width(), ho),
            QRect(area.left(), top + ho, area.width(), hn))


def draw_two_lines(painter, owner, name, owner_rect, name_rect, owner_font, name_font, color):
    painter.save()
    painter.setPen(color)
    flags = Qt.AlignLeft | Qt.AlignVCenter | Qt.TextSingleLine
    if owner_rect is not None:
        painter.setFont(owner_font)
        painter.drawText(owner_rect, flags, painter.fontMetrics().elidedText(owner, Qt.ElideRight, owner_rect.width()))
    painter.setFont(name_font)
    painter.drawText(name_rect, flags, painter.fontMetrics().elidedText(name, Qt.ElideRight, name_rect.width()))
    painter.restore()


class DeviceItemDelegate(QStyledItemDelegate):
    """Draws the popup rows with the same two-line layout as the closed selector."""

    def __init__(self, combobox):
        super().__init__(combobox)
        self.combobox = combobox

    def paint(self, painter, option, index):
        opt = type(option)(option)
        self.initStyleOption(opt, index)
        opt.text = ""
        opt.icon = QIcon()
        style = opt.widget.style() if opt.widget else self.combobox.style()
        style.drawControl(QStyle.CE_ItemViewItem, opt, painter, opt.widget)

        owner, name = self.combobox.item_lines(index.row())
        area = opt.rect.adjusted(COMBOBOX_PADDING_LEFT, 0, -FRAME, 0)
        owner_rect, name_rect = two_line_layout(area, owner, self.combobox.owner_font(), self.combobox.name_font())
        role = QPalette.HighlightedText if opt.state & QStyle.State_Selected else QPalette.Text
        draw_two_lines(painter, owner, name, owner_rect, name_rect, self.combobox.owner_font(),
                       self.combobox.name_font(), opt.palette.color(role))

    def sizeHint(self, option, index):
        owner, name = self.combobox.item_lines(index.row())
        height = QFontMetrics(self.combobox.name_font()).height() + 2 * FRAME
        if owner:
            height += QFontMetrics(self.combobox.owner_font()).height()
        return QSize(self.combobox.line_width(owner, name) + COMBOBOX_PADDING_LEFT + FRAME, height)


class DeviceComboBox(QComboBox):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(DeviceItemDelegate(self))

    # --- items -------------------------------------------------------------------------------------------------
    def add_device(self, dev):
        """Adds dev.title() as the item text (currentText() stays the full title) with the two lines as data."""
        self.addItem(dev.title())
        self.setItemData(self.count() - 1, split_title(dev), Qt.UserRole)

    def item_lines(self, row):
        data = self.itemData(row, Qt.UserRole)
        if isinstance(data, (tuple, list)) and len(data) == 2:
            return data[0], data[1]
        return "", self.itemText(row)

    def item_owner(self, row):
        return self.item_lines(row)[0]

    def item_name(self, row):
        return self.item_lines(row)[1]

    # --- fonts & geometry ----------------------------------------------------------------------------------------
    def name_font(self):
        return QFont(self.font())

    def owner_font(self):
        return owner_font_for(self.font())

    def line_width(self, owner, name):
        return max(QFontMetrics(self.owner_font()).horizontalAdvance(owner) if owner else 0,
                   QFontMetrics(self.name_font()).horizontalAdvance(name))

    def arrow_width(self):
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        w = self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxArrow, self).width()
        return w if w > 0 else ARROW_FALLBACK_WIDTH

    def text_area(self):
        """Where the two lines go: right of the stylesheet's left padding, left of the drop-down arrow."""
        return self.rect().adjusted(COMBOBOX_PADDING_LEFT, FRAME, -(self.arrow_width() + FRAME), -FRAME)

    def text_layout(self, row):
        owner, name = self.item_lines(row)
        return two_line_layout(self.text_area(), owner, self.owner_font(), self.name_font())

    def sizeHint(self):
        longest = max((self.line_width(*self.item_lines(r)) for r in range(self.count())), default=0)
        width = COMBOBOX_PADDING_LEFT + longest + self.arrow_width() + 2 * FRAME + 2
        height = QFontMetrics(self.owner_font()).height() + QFontMetrics(self.name_font()).height() + 2 * FRAME + 4
        return QSize(width, max(height, self.minimumHeight()))

    def minimumSizeHint(self):
        return self.sizeHint()

    # --- painting ------------------------------------------------------------------------------------------------
    def paintEvent(self, event):
        painter = QStylePainter(self)
        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        opt.currentText = ""       # frame and arrow only; the text is drawn on two lines below
        opt.currentIcon = QIcon()
        painter.drawComplexControl(QStyle.CC_ComboBox, opt)

        row = self.currentIndex()
        if row < 0:
            return
        owner, name = self.item_lines(row)
        owner_rect, name_rect = self.text_layout(row)
        group = QPalette.Active if self.isEnabled() else QPalette.Disabled
        draw_two_lines(painter, owner, name, owner_rect, name_rect, self.owner_font(), self.name_font(),
                       self.palette().color(group, QPalette.Text))
