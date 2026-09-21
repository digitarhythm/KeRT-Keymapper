import lzma
import os.path
import struct

import pytest

from PyQt5.QtCore import QPoint
from PyQt5.QtWidgets import QPushButton
from pytestqt.qt_compat import qt_api

from keycodes.keycodes import Keycode
from main_window import MainWindow

from protocol.constants import CMD_VIA_GET_PROTOCOL_VERSION, CMD_VIA_VIAL_PREFIX, CMD_VIAL_GET_KEYBOARD_ID, \
    CMD_VIAL_GET_SIZE, CMD_VIAL_GET_DEFINITION, CMD_VIA_GET_LAYER_COUNT, CMD_VIA_MACRO_GET_COUNT, \
    CMD_VIA_MACRO_GET_BUFFER_SIZE, CMD_VIA_MACRO_SET_BUFFER, CMD_VIAL_QMK_SETTINGS_QUERY, CMD_VIAL_DYNAMIC_ENTRY_OP, \
    DYNAMIC_VIAL_GET_NUMBER_OF_ENTRIES, CMD_VIA_KEYMAP_GET_BUFFER, CMD_VIA_MACRO_GET_BUFFER, CMD_VIAL_GET_UNLOCK_STATUS, \
    CMD_VIA_SET_KEYCODE, DYNAMIC_VIAL_COMBO_GET, DYNAMIC_VIAL_COMBO_SET, DYNAMIC_VIAL_TAP_DANCE_GET, \
    DYNAMIC_VIAL_TAP_DANCE_SET
from widgets.square_button import SquareButton

FAKE_KEYBOARD = """
{
  "matrix": {
    "rows": 2,
    "cols": 2
  },
  "layouts": {
    "keymap": [
      [
        "0,0",
        "0,1"
      ],
      [
        "1,0",
        "1,1"
      ]
    ]
  }
}
"""


def mock_enumerate():
    return [{
        "vendor_id": 0xDEAD,
        "product_id": 0xBEEF,
        "serial_number": "vial:f64c2b3c",
        "usage_page": 0xFF60,
        "usage": 0x61,
        "path": "/magic/path/for/tests",
        "manufacturer_string": "Vial Testing Ltd",
        "product_string": "Test Keyboard",
    }]


class VirtualKeyboard:

    def __init__(self, kbjson, combos=None, tap_dance=None, macro_buffer=None):
        if combos is None:
            combos = []
        if tap_dance is None:
            tap_dance = []

        self.keyboard_definition = lzma.compress(kbjson.encode("utf-8"))

        self.rows = 2
        self.cols = 2
        self.layers = 4
        self.keymap = []
        for layer in range(self.layers):
            self.keymap.append([])
            for row in range(self.rows):
                self.keymap[-1].append([0 for x in range(self.cols)])

        self.macro_count = 8
        self.macro_buffer = macro_buffer if macro_buffer is not None else b"\x00" * 512

        self.combos = combos
        self.tap_dance = tap_dance

        self.key_override_entries = 0
        self.alt_repeat_key_entries = 0

    def get_keymap_buffer(self):
        output = b""
        for layer in range(self.layers):
            for row in range(self.rows):
                for col in range(self.cols):
                    output += struct.pack(">H", self.keymap[layer][row][col])
        return output

    def vial_cmd_dynamic(self, msg):
        if msg[2] == DYNAMIC_VIAL_GET_NUMBER_OF_ENTRIES:
            response = struct.pack("BBBB", len(self.tap_dance), len(self.combos),
                                   self.key_override_entries, self.alt_repeat_key_entries)
            # Zero pad to 31 bytes.
            response += (31 - len(response)) * b'\0'
            # Set last two bits, indicating Caps Word and Layer Lock.
            response += (0b00000011).to_bytes(1, "little")
            return response
        elif msg[2] == DYNAMIC_VIAL_COMBO_GET:
            idx = msg[3]
            assert idx < len(self.combos)
            return struct.pack("<BHHHHH", 0, *self.combos[idx])
        elif msg[2] == DYNAMIC_VIAL_COMBO_SET:
            idx = msg[3]
            keys = struct.unpack_from("<HHHHH", msg[4:])
            assert idx < len(self.combos)
            self.combos[idx] = keys
            return b""
        elif msg[2] == DYNAMIC_VIAL_TAP_DANCE_GET:
            idx = msg[3]
            assert idx < len(self.tap_dance)
            return struct.pack("<BHHHHH", 0, *self.tap_dance[idx])
        elif msg[2] == DYNAMIC_VIAL_TAP_DANCE_SET:
            idx = msg[3]
            values = struct.unpack_from("<HHHHH", msg[4:])
            assert idx < len(self.tap_dance)
            self.tap_dance[idx] = values
            return b""
        raise RuntimeError("unsupported dynamic submsg 0x{:02X}".format(msg[2]))

    def vial_cmd(self, msg):
        if msg[1] == CMD_VIAL_GET_KEYBOARD_ID:
            return struct.pack("<IQ", 6, 0xF00DFACEDEADBEEF)
        elif msg[1] == CMD_VIAL_GET_SIZE:
            return struct.pack("<I", len(self.keyboard_definition))
        elif msg[1] == CMD_VIAL_GET_DEFINITION:
            page = struct.unpack_from("<H", msg[2:])[0]
            return self.keyboard_definition[page*32:(page+1)*32]
        elif msg[1] == CMD_VIAL_GET_UNLOCK_STATUS:
            return struct.pack("<BB", 0, 0)  # TODO we want to test unlocking as well
        elif msg[1] == CMD_VIAL_QMK_SETTINGS_QUERY:
            return b"\xFF" * 32
        elif msg[1] == CMD_VIAL_DYNAMIC_ENTRY_OP:
            return self.vial_cmd_dynamic(msg)
        raise RuntimeError("unknown command for Vial protocol 0x{:02X}".format(msg[1]))

    def process(self, msg):
        if msg[0] == CMD_VIA_VIAL_PREFIX:
            return self.vial_cmd(msg)
        elif msg[0] == CMD_VIA_GET_PROTOCOL_VERSION:
            return struct.pack(">BH", msg[0], 9)
        elif msg[0] == CMD_VIA_SET_KEYCODE:
            layer, row, col, kc = struct.unpack_from(">BBBH", msg[1:])
            self.keymap[layer][row][col] = kc
            return b""
        elif msg[0] == CMD_VIA_MACRO_GET_COUNT:
            return struct.pack(">BB", msg[0], self.macro_count)
        elif msg[0] == CMD_VIA_MACRO_GET_BUFFER_SIZE:
            return struct.pack(">BH", msg[0], len(self.macro_buffer))
        elif msg[0] == CMD_VIA_MACRO_GET_BUFFER:
            offset, size = struct.unpack_from(">HB", msg[1:])
            # the reply echoes the 4-byte request header (cmd, offset, size) before the data
            return msg[0:4] + self.macro_buffer[offset:offset+size]
        elif msg[0] == CMD_VIA_MACRO_SET_BUFFER:
            offset, size = struct.unpack_from(">HB", msg[1:])
            chunk = bytes(msg[4:4 + size])
            self.macro_buffer = self.macro_buffer[:offset] + chunk + self.macro_buffer[offset + size:]
            return msg[0:4]
        elif msg[0] == CMD_VIA_GET_LAYER_COUNT:
            return struct.pack(">BB", msg[0], self.layers)
        elif msg[0] == CMD_VIA_KEYMAP_GET_BUFFER:
            offset, size = struct.unpack_from(">HB", msg[1:])
            return msg[0:1] + self.get_keymap_buffer()[offset:offset+size]
        raise RuntimeError("unknown command for VIA protocol 0x{:02X}".format(msg[0]))


class MockDevice:

    def open_path(self, path):
        assert path == "/magic/path/for/tests"

    def close(self):
        pass

    def write(self, data):
        assert len(data) == 33
        assert data[0] == 0
        self.msg = data[1:]

        return len(data)

    def read(self, sz, timeout_ms=None):
        assert sz == 32
        resp = self.vk.process(self.msg)
        assert len(resp) <= 32
        resp += b"\x00" * (32 - len(resp))
        return resp


class FakeAppctx:

    def get_resource(self, path):
        return os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../resources/base/", path)


all_mw = []


def prepare(qtbot, keyboard_json, combos=None, tap_dance=None, macro_buffer=None):
    import hidraw as hid
    from PyQt5 import sip
    from util import KeycodeDisplay

    # qtbot deletes the previous test's MainWindow via deleteLater(); once the event loop has run, its
    # TabbedKeycodes are gone on the C++ side but still registered here, so drop them before building a new one
    KeycodeDisplay.clients = [c for c in KeycodeDisplay.clients if not sip.isdeleted(c)]

    vk = VirtualKeyboard(keyboard_json, combos=combos, tap_dance=tap_dance, macro_buffer=macro_buffer)
    MockDevice.vk = vk

    hid.enumerate = mock_enumerate
    hid.device = MockDevice

    mw = MainWindow(FakeAppctx())
    qtbot.addWidget(mw)
    mw.show()
    # keep reference to MainWindow for the duration of tests
    # when MainWindow goes out of scope some KeyWidgets are still registered within KeycodeDisplay which causes UaF
    all_mw.append(mw)

    return mw, vk


def test_gui_startup(qtbot):
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    assert mw.combobox_devices.currentText() == "Vial Testing Ltd Test Keyboard"
    assert mw.combobox_devices.count() == 1


def test_about_keyboard(qtbot):
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)

    mw.about_menu.actions()[0].trigger()
    assert mw.about_dialog.windowTitle() == "About Vial Testing Ltd Test Keyboard"
    assert mw.about_dialog.textarea.toPlainText() == ('Manufacturer: Vial Testing Ltd\n'
         'Product: Test Keyboard\n'
         'VID: DEAD\n'
         'PID: BEEF\n'
         'Device: /magic/path/for/tests\n'
         '\n'
         'VIA protocol: 9\n'
         'Vial protocol: 6\n'
         'Vial keyboard ID: F00DFACEDEADBEEF\n'
         '\n'
         'Macro entries: 8\n'
         'Macro memory: 512 bytes\n'
         'Macro delays: yes\n'
         'Complex (2-byte) macro keycodes: yes\n'
         '\n'
         'Tap Dance entries: unsupported - disabled in firmware\n'
         'Combo entries: unsupported - disabled in firmware\n'
         'Key Override entries: unsupported - disabled in firmware\n'
         'Alt Repeat Key entries: unsupported - disabled in firmware\n'
         'Caps Word: yes\n'
         'Layer Lock: yes\n'
         '\n'
         'QMK Settings: disabled in firmware\n')
    mw.about_dialog.accept()


def test_key_change(qtbot):
    """ Tests changing keys in a keymap """
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)

    # nothing should be selected yet in the keyboard display
    assert mw.keymap_editor.container.active_key is None

    # initial keycode must be KC_NO
    assert vk.keymap[0][0][0] == 0

    # clicking on first key must activate it
    point = mw.keymap_editor.container.widgets[0].bbox[0]
    qtbot.mouseClick(mw.keymap_editor.container, qt_api.QtCore.Qt.MouseButton.LeftButton,
                     pos=QPoint(int(point.x()), int(point.y())))

    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[0]

    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    bk = mw.keymap_editor.tabbed_keycodes.basic_keycodes

    # at this point we can select all keycodes so basic should be hidden
    assert ak.isVisible()
    assert not bk.isVisible()

    # change current key to B
    assert ak.currentIndex() == 0
    assert ak.tabText(ak.currentIndex()) == "Basic"
    btn = ak.widget(0).layout.itemAt(3).widget().buttons[3]
    assert btn.text == "B"
    qtbot.mouseClick(btn, qt_api.QtCore.Qt.MouseButton.LeftButton)

    # check the new keycode is KC_B
    assert vk.keymap[0][0][0] == 5

    # check that we moved to the next key after setting the first key
    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[1]

    def find_key_btn(start, text):
        for w in start.findChildren(SquareButton):
            if w.isVisible() and w.text == text:
                return w
        raise RuntimeError("cannot find a visible key button with text='{}'".format(text))

    # switch to the Quantum tab
    ak.setCurrentIndex(3)
    assert ak.tabText(ak.currentIndex()) == "Quantum"

    # change current key to a masked LCTL()
    btn = find_key_btn(ak, "LCtl\n(kc)")
    qtbot.mouseClick(btn, qt_api.QtCore.Qt.MouseButton.LeftButton)

    # check the new keycode is LCTL()
    assert vk.keymap[0][0][1] == 0x100

    # check that we moved to the next key after setting the second key
    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[2]

    # click back on the second key
    point = mw.keymap_editor.container.widgets[1].bbox[0]
    qtbot.mouseClick(mw.keymap_editor.container, qt_api.QtCore.Qt.MouseButton.LeftButton,
                     pos=QPoint(int(point.x()), int(point.y())))

    # check that we have the second key selected & it's not a mask
    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[1]
    assert not mw.keymap_editor.container.active_mask

    # click on the mask now by manually calculating somewhere within last 4/5th Y, midpoint X
    bbox = mw.keymap_editor.container.widgets[1].bbox
    min_x = min(p.x() for p in bbox)
    max_x = max(p.x() for p in bbox)
    min_y = min(p.y() for p in bbox)
    max_y = max(p.y() for p in bbox)
    qtbot.mouseClick(mw.keymap_editor.container, qt_api.QtCore.Qt.MouseButton.LeftButton,
                     pos=QPoint(int((min_x + max_x) / 2), int(min_y + (max_y - min_y) * 4/5)))
    # now we must have the inner selected on the same key
    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[1]
    assert mw.keymap_editor.container.active_mask

    # now only basic keys should be settable
    assert not ak.isVisible()
    assert bk.isVisible()

    # let's set key C
    btn = find_key_btn(bk, "C")
    qtbot.mouseClick(btn, qt_api.QtCore.Qt.MouseButton.LeftButton)

    # check the new keycode is LCTL(KC_C)
    assert vk.keymap[0][0][1] == 0x106

    # and we should have moved to the next key, setting the full key and not the inner
    assert mw.keymap_editor.container.active_key == mw.keymap_editor.container.widgets[2]
    assert not mw.keymap_editor.container.active_mask
    assert ak.isVisible()
    assert not bk.isVisible()


def test_keymap_zoom(qtbot):
    """ Tests zooming keymap in/out using +/- keys """
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)

    btn_plus = mw.keymap_editor.layout_size.itemAt(0).widget()
    btn_minus = mw.keymap_editor.layout_size.itemAt(1).widget()
    # TODO: resolve this field collision, +/- are SquareButton which overrides text
    assert QPushButton.text(btn_plus) == "+"
    assert QPushButton.text(btn_minus) == "-"

    # grab area for first widget
    scale_initial = mw.keymap_editor.container.scale

    # click the plus button
    qtbot.mouseClick(btn_plus, qt_api.QtCore.Qt.MouseButton.LeftButton)
    # area got bigger
    assert mw.keymap_editor.container.scale > scale_initial

    # click the minus button
    qtbot.mouseClick(btn_minus, qt_api.QtCore.Qt.MouseButton.LeftButton)
    # area back to the initial
    assert abs(mw.keymap_editor.container.scale - scale_initial) < 0.01

    # click the minus button
    qtbot.mouseClick(btn_minus, qt_api.QtCore.Qt.MouseButton.LeftButton)
    # area got smaller
    assert mw.keymap_editor.container.scale < scale_initial


def find_key_btn(start, text):
    for w in start.findChildren(SquareButton):
        if w.isVisible() and w.text == text:
            return w
    raise RuntimeError("cannot find a visible key button with text='{}'".format(text))


def test_layer_switch(qtbot):
    """ Tests setting keycodes across different layers """
    mw, vk = prepare(qtbot, FAKE_KEYBOARD)

    ak = mw.keymap_editor.tabbed_keycodes.all_keycodes
    bk = mw.keymap_editor.tabbed_keycodes.basic_keycodes
    c = mw.keymap_editor.container

    # initial keycode must be KC_NO
    assert vk.keymap[0][0][0] == 0

    # clicking on first key must activate it
    point = c.widgets[0].bbox[0]
    qtbot.mouseClick(c, qt_api.QtCore.Qt.MouseButton.LeftButton,
                     pos=QPoint(int(point.x()), int(point.y())))
    assert c.active_key == c.widgets[0]

    # change current key to Z
    qtbot.mouseClick(find_key_btn(ak, "Z"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.keymap[0][0][0] == 0x1D
    assert vk.keymap[1][0][0] == 0

    # make sure display for the widget now says Z
    assert c.widgets[0].text == "Z"
    # and that the next key is selected
    assert c.active_key == c.widgets[1]
    assert not c.active_mask

    # go to layer 1
    btn_layer_0 = mw.keymap_editor.layer_buttons[0]
    btn_layer_1 = mw.keymap_editor.layer_buttons[1]
    # TODO: resolve this field collision, +/- are SquareButton which overrides text
    assert QPushButton.text(btn_layer_0) == "0"
    assert QPushButton.text(btn_layer_1) == "1"

    qtbot.mouseClick(btn_layer_1, qt_api.QtCore.Qt.MouseButton.LeftButton)
    # check the current key got deselected
    assert c.active_key is None
    assert not c.active_mask

    # check the widget now displays layer 1 data, i.e. empty string as it's not set yet
    assert c.widgets[0].text == ""

    # click the key again
    qtbot.mouseClick(c, qt_api.QtCore.Qt.MouseButton.LeftButton,
                     pos=QPoint(int(point.x()), int(point.y())))
    assert c.active_key == c.widgets[0]

    # change current key to Y
    qtbot.mouseClick(find_key_btn(ak, "Y"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.keymap[0][0][0] == 0x1D
    assert vk.keymap[1][0][0] == 0x1C

    # make sure display for the widget now says Y
    assert c.widgets[0].text == "Y"

    # go back to the layer 0 and make sure the button got redrawn to Z
    qtbot.mouseClick(btn_layer_0, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert c.widgets[0].text == "Z"


def key_pos(keywidget):
    """ A point on the outer part of the (single) key drawn by a KeyWidget, as an int QPoint for
    qtbot.mouseClick. Near the top-left corner so that it never lands on the inner mask of a masked key """
    bbox = keywidget.widgets[0].bbox
    sc = keywidget.scale   # bbox is in unscaled coordinates; cards draw their keys smaller
    return QPoint(int(min(p.x() for p in bbox) * sc) + 3, int(min(p.y() for p in bbox) * sc) + 3)


def key_mask_pos(keywidget):
    """ A point inside the inner (mask) part of a masked key """
    bbox = keywidget.widgets[0].bbox
    sc = keywidget.scale
    min_x = min(p.x() for p in bbox) * sc
    max_x = max(p.x() for p in bbox) * sc
    min_y = min(p.y() for p in bbox) * sc
    max_y = max(p.y() for p in bbox) * sc
    return QPoint(int((min_x + max_x) / 2), int(min_y + (max_y - min_y) * 4 / 5))


def card_headers(editor):
    return [c.header.text() for c in editor.cards]


def test_combos(qtbot):
    """ Combos are shown as cards (all entries at once) and edited in place """
    from widgets.key_widget import KeyWidget

    mw, vk = prepare(qtbot, FAKE_KEYBOARD, combos=[[0, 0, 0, 0, 0], [4, 5, 6, 7, 8], [0, 0x106, 0, 0, 0]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    combos = find_tab(mw, "Combos").editor
    assert card_headers(combos) == ["Combo 1", "Combo 2", "Combo 3"]

    def check_card(idx, keys):
        w = combos.cards[idx].findChildren(KeyWidget)
        assert len(w) == 5
        for x in range(5):
            assert w[x].keycode == keys[x], "unexpected keycode at card {} position {}: {} vs {}".format(idx, x, w[x].keycode, keys[x])

    check_card(0, ["KC_NO", "KC_NO", "KC_NO", "KC_NO", "KC_NO"])
    check_card(1, ["KC_A", "KC_B", "KC_C", "KC_D", "KC_E"])
    check_card(2, ["KC_NO", "LCTL(KC_C)", "KC_NO", "KC_NO", "KC_NO"])

    # card 3: change "Key 1" to "A"
    assert not mw.tray_keycodes.isVisible()
    w = combos.cards[2].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    assert mw.tray_keycodes.isVisible()
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "A"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.combos[2] == (4, 0x106, 0, 0, 0)

    # change "Output key" to "B"
    qtbot.mouseClick(w[4], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[4]))
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "B"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.combos[2] == (4, 0x106, 0, 0, 5)

    ak = mw.tray_keycodes.all_keycodes
    bk = mw.tray_keycodes.basic_keycodes

    # change "Key 4" to LSft(D): first the mask, then the key inside it
    qtbot.mouseClick(w[3], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[3]))
    assert ak.isVisible() and not bk.isVisible()
    ak.setCurrentIndex(3)
    assert ak.tabText(ak.currentIndex()) == "Quantum"
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "LSft\n(kc)"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.combos[2] == (4, 0x106, 0, 0x200, 5)
    qtbot.mouseClick(w[3], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_mask_pos(w[3]))
    assert not ak.isVisible() and bk.isVisible()
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "D"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.combos[2] == (4, 0x106, 0, 0x207, 5)

    # change "Key 2" to E
    qtbot.mouseClick(w[1], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[1]))
    assert ak.isVisible() and not bk.isVisible()
    ak.setCurrentIndex(0)
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "E"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.combos[2] == (4, 8, 0, 0x207, 5)

    check_card(2, ["KC_A", "KC_E", "KC_NO", "LSFT(KC_D)", "KC_B"])


def test_tap_dance(qtbot):
    """ Tap dances are shown as cards with their tapping term in the header and edited in place """
    from widgets.key_widget import KeyWidget
    from PyQt5.QtWidgets import QSpinBox

    mw, vk = prepare(qtbot, FAKE_KEYBOARD, tap_dance=[[0, 0, 0, 0, 200], [4, 5, 6, 7, 200], [0, 0x106, 0, 0, 500]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    tde = find_tab(mw, "Tap Dance").editor
    assert card_headers(tde) == ["TD(0)  200ms", "TD(1)  200ms", "TD(2)  500ms"]
    assert "TD(n)" in tde.hint.text()
    assert all(c.sizeHint().width() == c.sizeHint().height() for c in tde.cards)

    def check_card(idx, keys, timeout):
        card = tde.cards[idx]
        w = card.findChildren(KeyWidget)
        assert len(w) == 4
        for x in range(4):
            assert w[x].keycode == keys[x], "unexpected keycode at card {} position {}: {} vs {}".format(idx, x, w[x].keycode, keys[x])
        assert card.findChildren(QSpinBox)[0].value() == timeout

    check_card(0, ["KC_NO", "KC_NO", "KC_NO", "KC_NO"], 200)
    check_card(1, ["KC_A", "KC_B", "KC_C", "KC_D"], 200)
    check_card(2, ["KC_NO", "LCTL(KC_C)", "KC_NO", "KC_NO"], 500)

    # card TD(2): the keycode change is immediate but not the timeout change
    assert not mw.tray_keycodes.isVisible()
    w = tde.cards[2].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    assert mw.tray_keycodes.isVisible()
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "A"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.tap_dance[2] == (4, 0x106, 0, 0, 500)

    timeout_w = tde.cards[2].findChildren(QSpinBox)[0]
    timeout_w.setValue(123)
    assert vk.tap_dance[2] == (4, 0x106, 0, 0, 500)

    # pending changes are marked with * in the card header, and enable Save
    assert tde.cards[2].header.text() == "TD(2)  123ms*"
    assert tde.btn_save.isEnabled()
    timeout_w.setValue(500)
    assert tde.cards[2].header.text() == "TD(2)  500ms"
    assert not tde.btn_save.isEnabled()

    # commit
    timeout_w.setValue(123)
    qtbot.mouseClick(tde.btn_save, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert tde.cards[2].header.text() == "TD(2)  123ms"
    assert vk.tap_dance[2] == (4, 0x106, 0, 0, 123)

    # revert
    assert not tde.btn_save.isEnabled()
    timeout_w.setValue(321)
    assert tde.btn_save.isEnabled()
    assert tde.cards[2].header.text() == "TD(2)  321ms*"
    qtbot.mouseClick(tde.btn_revert, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert not tde.btn_save.isEnabled()
    assert tde.cards[2].header.text() == "TD(2)  123ms"
    assert timeout_w.value() == 123


FAKE_KEYBOARD_HOST_OS = """
{
  "matrix": {
    "rows": 2,
    "cols": 2
  },
  "layouts": {
    "keymap": [
      [
        "0,0",
        "0,1"
      ],
      [
        "1,0",
        "1,1"
      ]
    ]
  },
  "hostOS": {
    "count": 2
  }
}
"""

HOST_OS_MARKER = 0x4F53


def find_tab(mw, label):
    """ Returns the EditorContainer for the main window tab with the given label, or None """
    for x in range(mw.tabs.count()):
        if mw.tabs.tabText(x) == label:
            return mw.tabs.widget(x)
    return None


def tray_tab_names(mw):
    ak = mw.tray_keycodes.all_keycodes
    return [ak.tabText(x) for x in range(ak.count())]


def test_host_os_hidden_without_definition(qtbot):
    """ Without "hostOS" in the definition there is no HostOS tab and Tap Dance shows every slot """
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, tap_dance=[[0, 0, 0, 0, 200] for _ in range(4)])

    assert find_tab(mw, "HostOS") is None
    assert "HostOS" not in tray_tab_names(mw)
    kb = mw.autorefresh.current_device.keyboard
    assert kb.host_os_count == 0

    tde = find_tab(mw, "Tap Dance").editor
    assert len(tde.cards) == 4


def test_host_os(qtbot):
    """ The last hostOS.count tap dance slots are edited as (Mac, Win, Linux, Default) and keyed by HOS(n) """
    import json
    from PyQt5.QtWidgets import QLabel, QPushButton, QSpinBox
    from widgets.key_widget import KeyWidget

    # 4 tap dance slots, hostOS.count = 2: slots 0..1 are tap dances, slots 2..3 are HostOS 0..1
    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS, tap_dance=[
        [0, 0, 0, 0, 200],
        [4, 5, 6, 7, 200],
        [0x14, 0x1A, 0x08, 0x15, HOST_OS_MARKER],   # Q, W, E, R -> Mac, Win, Linux, Default (seeded marker)
        [0, 0, 0, 0x1B, 500],                       # only Default set (X); marker not yet written
    ])
    # on macOS the central widget only becomes visible once queued show events are processed
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    kb = mw.autorefresh.current_device.keyboard
    assert (kb.tap_dance_count, kb.host_os_count, kb.host_os_base) == (4, 2, 2)

    # Tap Dance keeps only the slots below base; HostOS sits right after it
    main_tabs = [mw.tabs.tabText(x) for x in range(mw.tabs.count())]
    assert main_tabs.index("HostOS") == main_tabs.index("Tap Dance") + 1
    tde = find_tab(mw, "Tap Dance").editor
    assert card_headers(tde) == ["TD(0)  200ms", "TD(1)  200ms"]

    container = find_tab(mw, "HostOS")
    assert container is not None, "could not find the HostOS tab"
    hoe = container.editor
    assert card_headers(hoe) == ["HOS(0)", "HOS(1)"]
    # one hint for the whole tab instead of one per card
    hint = hoe.hint.text()
    assert "HOS(n)" in hint and "Default" in hint
    assert "TD(" not in hint          # the tap dance slot behind a HostOS key is an implementation detail

    # every keycode change is stored immediately, so there is nothing for Save / Revert to do
    assert [b.text() for b in container.findChildren(QPushButton) if b.text() in ("Save", "Revert")] == []

    def check_tab(idx, keys):
        page = hoe.cards[idx]

        w = page.findChildren(KeyWidget)
        assert len(w) == 4
        for x in range(4):
            assert w[x].keycode == keys[x], "unexpected keycode at tab {} position {}: {} vs {}".format(
                idx, x, w[x].keycode, keys[x])
        # the marker / tapping term is not exposed
        assert page.findChildren(QSpinBox) == []

        labels = [l.text() for l in page.findChildren(QLabel) if l is not page.header]
        assert labels == ["Mac", "Win", "Linux", "Default"]
        # cards are square (hidden tabs may not be laid out yet, so check the requested size)
        assert page.sizeHint().width() == page.sizeHint().height()

    check_tab(0, ["KC_Q", "KC_W", "KC_E", "KC_R"])
    check_tab(1, ["KC_NO", "KC_NO", "KC_NO", "KC_X"])

    # card HOS(1): set the Mac keycode to "A"
    assert not mw.tray_keycodes.isVisible()
    w = hoe.cards[1].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    assert mw.tray_keycodes.isVisible()

    # the keycode list has a "HostOS" tab with HOS(n) right after "Tap Dance", which only has TD(0..base-1)
    ak = mw.tray_keycodes.all_keycodes
    tray_tabs = {ak.tabText(x): x for x in range(ak.count())}
    assert tray_tabs["HostOS"] == tray_tabs["Tap Dance"] + 1
    ak.setCurrentIndex(tray_tabs["Tap Dance"])
    for text in ["TD(0)", "TD(1)"]:
        assert find_key_btn(mw.tray_keycodes, text) is not None
    for text in ["TD(2)", "TD(3)", "HOS(0)"]:
        with pytest.raises(RuntimeError):
            find_key_btn(mw.tray_keycodes, text)
    ak.setCurrentIndex(tray_tabs["HostOS"])
    for text in ["HOS(0)", "HOS(1)"]:
        assert find_key_btn(mw.tray_keycodes, text) is not None
    with pytest.raises(RuntimeError):
        find_key_btn(mw.tray_keycodes, "TD(2)")
    ak.setCurrentIndex(0)
    assert ak.tabText(ak.currentIndex()) == "Basic"

    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "A"), qt_api.QtCore.Qt.MouseButton.LeftButton)

    # written straight to tap dance slot base + 1 = 3, with the seeded marker in the fifth field
    assert vk.tap_dance[3] == (4, 0, 0, 0x1B, HOST_OS_MARKER)
    assert vk.tap_dance[2] == [0x14, 0x1A, 0x08, 0x15, HOST_OS_MARKER]
    assert vk.tap_dance[1] == [4, 5, 6, 7, 200]
    assert hoe.cards[1].header.text() == "HOS(1)"

    # HOS(n) is only a spelling of TD(base + n)
    assert Keycode.deserialize("HOS(1)") == Keycode.deserialize("TD(3)")
    assert Keycode.label("TD(3)") == "HOS(1)"
    assert Keycode.serialize(Keycode.deserialize("HOS(1)")) == "TD(3)"

    # KC_TRNS means "empty": it is written as KC_NO and the UI is synced to what was actually stored
    fields = hoe.cards[1].findChildren(KeyWidget)
    fields[1].set_keycode("KC_B")       # Win
    fields[2].set_keycode("KC_TRNS")    # Linux -> stored as KC_NO
    assert vk.tap_dance[3] == (4, 5, 0, 0x1B, HOST_OS_MARKER)
    assert kb.tap_dance_get(3) == ("KC_A", "KC_B", "KC_NO", "KC_X", HOST_OS_MARKER)
    assert [k.keycode for k in fields] == ["KC_A", "KC_B", "KC_NO", "KC_X"]

    # .vil: unchanged format, the HostOS slots are simply the last entries of "tap_dance"
    layout = json.loads(kb.save_layout())
    assert layout["tap_dance"][2] == ["KC_Q", "KC_W", "KC_E", "KC_R", HOST_OS_MARKER]
    assert layout["tap_dance"][3] == ["KC_A", "KC_B", "KC_NO", "KC_X", HOST_OS_MARKER]


def test_host_os_count_clamped(qtbot):
    """ A count larger than the tap dance slot count is clamped: every slot becomes HostOS """
    fake = FAKE_KEYBOARD_HOST_OS.replace('"count": 2', '"count": 50')
    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS.replace('"count": 2', '"count": 50'),
                     tap_dance=[[0, 0, 0, 0, 200] for _ in range(4)])

    kb = mw.autorefresh.current_device.keyboard
    assert (kb.host_os_count, kb.host_os_base) == (4, 0)
    container = find_tab(mw, "HostOS")
    assert container is not None
    assert card_headers(container.editor) == ["HOS(0)", "HOS(1)", "HOS(2)", "HOS(3)"]
    tde = find_tab(mw, "Tap Dance").editor
    assert tde.cards == []


def test_entry_cards_in_picker(qtbot):
    """ The Tap Dance / HostOS keycode pickers show each entry as the same card as the editor and follow edits """
    from PyQt5.QtWidgets import QLabel, QSpinBox
    from widgets.entry_card_button import EntryCardButton
    from widgets.key_widget import KeyWidget

    mw, vk = prepare(qtbot, FAKE_KEYBOARD_HOST_OS, tap_dance=[
        [4, 0xE1, 5, 0, 200],                     # TD(0): A / LShift / B / -
        [0x29, 0, 0, 0, 180],                     # TD(1): Esc / - / - / -
        [0x14, 0x1A, 0x08, 0x15, HOST_OS_MARKER], # HOS(0): Q / W / E / R
        [0, 0, 0, 0x1B, HOST_OS_MARKER],          # HOS(1): - / - / - / X
    ])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    def picker_buttons(tab_label):
        ak = mw.tray_keycodes.all_keycodes
        idx = [x for x in range(ak.count()) if ak.tabText(x) == tab_label][0]
        return {b.text: b for b in ak.widget(idx).findChildren(EntryCardButton)}

    def card_keys(btn):
        return [k.keycode for k in btn.findChildren(KeyWidget)]

    def card_labels(btn):
        return [l.text() for l in btn.findChildren(QLabel) if l is not btn.header]

    td = picker_buttons("Tap Dance")
    assert sorted(td) == ["TD(0)", "TD(1)"]
    assert td["TD(0)"].header.text() == "TD(0)  200ms"
    assert td["TD(1)"].header.text() == "TD(1)  180ms"
    assert card_labels(td["TD(0)"]) == ["On tap", "On hold", "On double tap", "On tap + hold"]
    assert card_keys(td["TD(0)"]) == ["KC_A", "KC_LSHIFT", "KC_B", "KC_NO"]
    assert card_keys(td["TD(1)"]) == ["KC_ESCAPE", "KC_NO", "KC_NO", "KC_NO"]
    tip = td["TD(0)"].toolTip()
    assert "Tap: A" in tip and "Hold: LShift" in tip and "Tapping term: 200 ms" in tip
    # the tray is hidden at this point, so check the requested size rather than the laid-out one
    assert all(b.sizeHint().width() == b.sizeHint().height() for b in td.values())

    ho = picker_buttons("HostOS")
    assert sorted(ho) == ["HOS(0)", "HOS(1)"]
    assert ho["HOS(0)"].header.text() == "HOS(0)"
    assert card_labels(ho["HOS(0)"]) == ["Mac", "Win", "Linux", "Default"]
    assert card_keys(ho["HOS(0)"]) == ["KC_Q", "KC_W", "KC_E", "KC_R"]
    assert card_keys(ho["HOS(1)"]) == ["KC_NO", "KC_NO", "KC_NO", "KC_X"]
    tip = ho["HOS(1)"].toolTip()
    assert "Mac: \u2014" in tip and "Default: X" in tip and "Tapping term" not in tip

    # editing an entry updates the picker cards
    hoe = find_tab(mw, "HostOS").editor
    w = hoe.cards[1].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "A"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.tap_dance[3] == (4, 0, 0, 0x1B, HOST_OS_MARKER)
    assert card_keys(picker_buttons("HostOS")["HOS(1)"]) == ["KC_A", "KC_NO", "KC_NO", "KC_X"]

    tde = find_tab(mw, "Tap Dance").editor
    w = tde.cards[1].findChildren(KeyWidget)
    qtbot.mouseClick(w[1], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[1]))
    qtbot.mouseClick(find_key_btn(mw.tray_keycodes, "B"), qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert vk.tap_dance[1] == (0x29, 5, 0, 0, 180)
    assert card_keys(picker_buttons("Tap Dance")["TD(1)"]) == ["KC_ESCAPE", "KC_B", "KC_NO", "KC_NO"]
    # the tapping term shown in the header follows a saved change too
    tde.cards[1].findChildren(QSpinBox)[0].setValue(250)
    qtbot.mouseClick(tde.btn_save, qt_api.QtCore.Qt.MouseButton.LeftButton)
    assert picker_buttons("Tap Dance")["TD(1)"].header.text() == "TD(1)  250ms"

    # a picker card still assigns its keycode wherever it is clicked: put TD(0) into the Mac field of HOS(0)
    w = hoe.cards[0].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    ak = mw.tray_keycodes.all_keycodes
    ak.setCurrentIndex([x for x in range(ak.count()) if ak.tabText(x) == "Tap Dance"][0])
    card = picker_buttons("Tap Dance")["TD(0)"]
    # click where a key is drawn inside the card, not on its margin (the children are transparent
    # for mouse events, so the click lands on the card button itself)
    inner_key = card.findChildren(KeyWidget)[2]
    qtbot.mouseClick(card, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=inner_key.mapTo(card, key_pos(inner_key)))
    assert vk.tap_dance[2] == (Keycode.deserialize("TD(0)"), 0x1A, 0x08, 0x15, HOST_OS_MARKER)
    assert w[0].keycode == "TD(0)"


def test_entry_card_container_closes_tray(qtbot):
    """ Clicking the empty area of a card list closes the keycode tray, like switching tabs used to """
    from widgets.key_widget import KeyWidget

    mw, vk = prepare(qtbot, FAKE_KEYBOARD, combos=[[0, 0, 0, 0, 0], [4, 5, 6, 7, 8]])
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    combos = find_tab(mw, "Combos").editor

    w = combos.cards[0].findChildren(KeyWidget)
    qtbot.mouseClick(w[0], qt_api.QtCore.Qt.MouseButton.LeftButton, pos=key_pos(w[0]))
    assert mw.tray_keycodes.isVisible()

    viewport = combos.container.viewport()
    empty = viewport.rect().bottomRight() - QPoint(2, 2)
    qtbot.mouseClick(viewport, qt_api.QtCore.Qt.MouseButton.LeftButton, pos=empty)
    assert not mw.tray_keycodes.isVisible()


def test_layer_buttons_vertical(qtbot):
    """ The layer buttons are stacked vertically under the "Layer" label, to the left of the keyboard """
    from PyQt5.QtWidgets import QLabel, QVBoxLayout

    mw, vk = prepare(qtbot, FAKE_KEYBOARD)
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())
    ke = mw.keymap_editor
    buttons = ke.layer_buttons[:4]     # 4 layers on the virtual keyboard; the +/- buttons follow

    assert isinstance(ke.layout_layers, QVBoxLayout)
    # the buttons are created on connect; give the layout a chance to place them
    qtbot.waitUntil(lambda: buttons[-1].mapToGlobal(buttons[-1].rect().topLeft()) != buttons[0].mapToGlobal(buttons[0].rect().topLeft()))
    xs = [b.mapToGlobal(b.rect().topLeft()).x() for b in buttons]
    ys = [b.mapToGlobal(b.rect().topLeft()).y() for b in buttons]
    assert len(set(xs)) == 1, "layer buttons must be in one column"
    assert ys == sorted(ys) and len(set(ys)) == 4, "layer buttons must be stacked top to bottom"

    label = ke.layer_label
    assert isinstance(label, QLabel) and label.text() == "Layer"
    assert label.mapToGlobal(label.rect().bottomLeft()).y() <= ys[0]

    # the column sits left of the keyboard
    kb_x = ke.container.mapToGlobal(ke.container.rect().topLeft()).x()
    assert xs[0] < kb_x

    # wide buttons: about three times as wide as tall
    for b in buttons:
        assert 2.5 <= b.width() / b.height() <= 3.5


def test_macro_cards_in_picker(qtbot):
    """ The Macro picker shows each macro as a card with its first four actions """
    from types import SimpleNamespace
    from PyQt5.QtWidgets import QLabel
    from macro.macro_action import ActionDelay, ActionTap, ActionText
    from protocol.macro import ProtocolMacro
    from widgets.entry_card_button import EntryCardButton

    proto = SimpleNamespace(vial_protocol=6)
    macros = [
        [ActionText("Hello"), ActionTap(["KC_A", "KC_B"]), ActionDelay(100), ActionText("x"), ActionDelay(5)],
        [],
    ]
    buf = b"\x00".join(ProtocolMacro.macro_serialize(proto, m) for m in macros) + b"\x00"
    mw, vk = prepare(qtbot, FAKE_KEYBOARD, macro_buffer=buf + b"\x00" * (512 - len(buf)))
    qtbot.waitUntil(lambda: mw.centralWidget().isVisible())

    ak = mw.tray_keycodes.all_keycodes
    idx = [x for x in range(ak.count()) if ak.tabText(x) == "Macro"][0]
    cards = {b.text: b for b in ak.widget(idx).findChildren(EntryCardButton)}
    assert "M0" in cards and "M1" in cards

    assert cards["M0"].header.text() == "M0"
    assert cards["M0"].lines == ["Text: Hello", "Tap: A + B", "Delay: 100 ms", "Text: x"]
    shown = [l.text() for l in cards["M0"].findChildren(QLabel) if l is not cards["M0"].header]
    assert shown == cards["M0"].lines
    assert cards["M1"].lines == ["\u2014"]
    # every macro card has the same size, whatever its contents
    assert cards["M0"].sizeHint() == cards["M1"].sizeHint()

    # editing a macro updates the card
    kb = mw.autorefresh.current_device.keyboard
    kb.set_macro(b"\x00".join(ProtocolMacro.macro_serialize(proto, m) for m in [[ActionText("Bye")], []]) + b"\x00")
    import entry_labels
    entry_labels.update(kb)
    cards = {b.text: b for b in ak.widget(idx).findChildren(EntryCardButton)}
    assert cards["M0"].lines == ["Text: Bye"]
