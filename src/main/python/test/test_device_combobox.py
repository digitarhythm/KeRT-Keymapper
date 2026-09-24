# SPDX-License-Identifier: GPL-2.0-or-later
"""Two-line keyboard selector: owner (manufacturer) in a half-size font above the keyboard name
(docs/theme-flat-keys-spec.md §4.2.1)."""
import os
import sys

from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QColor, QFontMetrics
from PyQt5.QtWidgets import QApplication

sys.path.insert(0, os.path.dirname(__file__))

OWNER = "Vial Testing Ltd"
NAME = "Test Keyboard"


class FakeDevice:
    def __init__(self, title, manufacturer=None):
        self._title = title
        self.desc = {"path": "/x"}
        if manufacturer is not None:
            self.desc["manufacturer_string"] = manufacturer

    def title(self):
        return self._title


def test_split_title():
    from widgets.device_combobox import split_title

    assert split_title(FakeDevice("Acme Pro 60 [VIA]", "Acme")) == ("Acme", "Pro 60 [VIA]")
    assert split_title(FakeDevice("Vial Bootloader [DEAD:BEEF]")) == ("", "Vial Bootloader [DEAD:BEEF]")
    assert split_title(FakeDevice("[Dummy Keyboard]")) == ("", "[Dummy Keyboard]")
    # a manufacturer that does not prefix the title is not stripped away
    assert split_title(FakeDevice("Other Name", "Acme")) == ("", "Other Name")
    assert split_title(FakeDevice("Test Keyboard", "")) == ("", "Test Keyboard")


def dark_pixels(image, rect):
    return sum(1 for x in range(rect.left(), rect.right() + 1) for y in range(rect.top(), rect.bottom() + 1)
               if QColor(image.pixel(x, y)).lightness() < 128)


def prepared(qtbot):
    from test_gui import prepare, FAKE_KEYBOARD

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    mw.resize(1700, 1000)
    cb = mw.combobox_devices
    qtbot.waitUntil(lambda: cb.width() >= cb.sizeHint().width())
    return mw, cb


def test_two_line_fonts(qtbot):
    from widgets.device_combobox import DeviceComboBox

    mw, cb = prepared(qtbot)
    assert isinstance(cb, DeviceComboBox)
    assert cb.item_owner(0) == OWNER and cb.item_name(0) == NAME
    assert cb.currentText() == OWNER + " " + NAME
    assert cb.name_font().pointSize() == cb.font().pointSize() == QApplication.font().pointSize() + 4
    assert cb.owner_font().pointSize() == round(cb.font().pointSize() / 2) + 2


def test_two_line_layout(qtbot):
    from widgets.device_combobox import DeviceComboBox

    mw, cb = prepared(qtbot)
    area = cb.text_area()
    owner_rect, name_rect = cb.text_layout(0)
    assert owner_rect is not None
    assert owner_rect.bottom() <= name_rect.top()
    assert owner_rect.height() < name_rect.height()
    assert area.contains(owner_rect) and area.contains(name_rect)
    assert owner_rect.left() == name_rect.left() >= 32

    single = DeviceComboBox()
    qtbot.addWidget(single)
    single.setFont(cb.font())
    single.setMinimumHeight(cb.minimumHeight())
    single.add_device(FakeDevice("Vial Bootloader [DEAD:BEEF]"))
    single.resize(cb.size())
    owner_rect, name_rect = single.text_layout(0)
    assert owner_rect is None
    centre = single.text_area().center().y()
    assert abs(name_rect.center().y() - centre) <= 1


def test_two_line_paint(qtbot):
    mw, cb = prepared(qtbot)
    owner_rect, name_rect = cb.text_layout(0)
    image = cb.grab().toImage()

    assert dark_pixels(image, owner_rect) > 0
    assert dark_pixels(image, name_rect) > 0
    between = QRect(owner_rect.left(), owner_rect.bottom() + 1, owner_rect.width(), name_rect.top() - owner_rect.bottom() - 1)
    assert between.height() == 0 or dark_pixels(image, between) == 0
    # the owner line is really smaller: fewer dark pixels than the (longer, larger) keyboard name line
    assert dark_pixels(image, owner_rect) < dark_pixels(image, name_rect) or len(OWNER) <= len(NAME)


def test_width_follows_longest_line(qtbot):
    mw, cb = prepared(qtbot)
    full = QFontMetrics(cb.name_font()).horizontalAdvance(OWNER + " " + NAME)
    longest = max(QFontMetrics(cb.name_font()).horizontalAdvance(NAME),
                  QFontMetrics(cb.owner_font()).horizontalAdvance(OWNER))
    assert cb.sizeHint().width() < full + 32
    assert cb.sizeHint().width() <= longest + 32 + 60   # padding-left + arrow + frame allowance
    assert cb.height() >= cb.minimumHeight()


def test_popup_delegate(qtbot):
    from PyQt5.QtWidgets import QStyleOptionViewItem
    from widgets.device_combobox import DeviceItemDelegate

    mw, cb = prepared(qtbot)
    delegate = cb.itemDelegate()
    assert isinstance(delegate, DeviceItemDelegate)
    hint = delegate.sizeHint(QStyleOptionViewItem(), cb.model().index(0, 0))
    assert hint.height() >= QFontMetrics(cb.owner_font()).height() + QFontMetrics(cb.name_font()).height()


def test_undefined_keyboard_name():
    """A device without a product name (RMK over Bluetooth reports none) is called "Undefined Keyboard" """
    from vial_device import VialKeyboard as VialDevice, UNDEFINED_KEYBOARD_NAME
    from widgets.device_combobox import split_title

    assert UNDEFINED_KEYBOARD_NAME == "Undefined Keyboard"
    ids = {"path": "/x", "vendor_id": 0x1209, "product_id": 0xFF09}
    for desc in ({**ids, "manufacturer_string": "", "product_string": ""},
                 {**ids, "manufacturer_string": None, "product_string": None},
                 dict(ids)):
        dev = VialDevice(desc)
        assert dev.title() == "Undefined Keyboard"
        assert split_title(dev) == ("", "Undefined Keyboard")
    # a manufacturer without a product name keeps the owner line
    dev = VialDevice({**ids, "manufacturer_string": "Acme", "product_string": None})
    assert dev.title() == "Acme Undefined Keyboard"
    assert split_title(dev) == ("Acme", "Undefined Keyboard")
    # a normal device is unchanged
    dev = VialDevice({**ids, "manufacturer_string": "Acme", "product_string": "Pro 60"})
    assert dev.title() == "Acme Pro 60"
