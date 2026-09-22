# SPDX-License-Identifier: GPL-2.0-or-later
import json

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QMessageBox, QSplitter, QWidget
from PyQt5.QtCore import Qt, pyqtSignal

from any_keycode_dialog import AnyKeycodeDialog
from editor.basic_editor import BasicEditor
from widgets.keyboard_widget import KeyboardWidget, EncoderWidget
from keycodes.keycodes import Keycode
from widgets.square_button import SquareButton
from tabbed_keycodes import TabbedKeycodes, keycode_filter_masked
from util import tr, KeycodeDisplay
from vial_device import VialKeyboard
from branding_theme import LAYOUT_SPACING

# keyboard (top) : keycode picker (bottom)
SPLIT_RATIO = (4, 6)
# auto-fit never enlarges the keys beyond this (tiny macro pads would otherwise fill the screen)
MAX_FIT_SCALE = 3.0


class RatioSplitter(QSplitter):
    """Vertical splitter that keeps its two panes at a fixed ratio until the user drags the handle."""

    def __init__(self, ratio):
        super().__init__(Qt.Vertical)
        self.ratio = ratio
        self.user_sized = False
        self.setChildrenCollapsible(False)
        self.setHandleWidth(LAYOUT_SPACING)
        self.splitterMoved.connect(self.on_moved)

    def on_moved(self, pos, index):
        self.user_sized = True

    def apply_ratio(self):
        total = self.height() - self.handleWidth() * (self.count() - 1)
        if total <= 0 or self.count() != len(self.ratio):
            return
        parts = sum(self.ratio)
        sizes = [total * r // parts for r in self.ratio]
        sizes[-1] += total - sum(sizes)
        self.setSizes(sizes)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if not self.user_sized:
            self.apply_ratio()


class ClickableWidget(QWidget):

    clicked = pyqtSignal()
    resized = pyqtSignal()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self.resized.emit()

    def mousePressEvent(self, evt):
        super().mousePressEvent(evt)
        self.clicked.emit()


class KeymapEditor(BasicEditor):

    def __init__(self, layout_editor):
        super().__init__()

        self.layout_editor = layout_editor

        # layer buttons stacked vertically under the "Layer" label, left of the keyboard;
        # zoom buttons in a column on the right
        self.layout_layers = QVBoxLayout()
        self.layout_size = QVBoxLayout()
        self.layer_label = QLabel(tr("KeymapEditor", "Layer"))

        layer_column = QVBoxLayout()
        layer_column.addWidget(self.layer_label)
        layer_column.setAlignment(self.layer_label, Qt.AlignHCenter)
        layer_column.addLayout(self.layout_layers)
        layer_column.addStretch()

        size_column = QVBoxLayout()
        size_column.addLayout(self.layout_size)
        size_column.addStretch()

        # contains the actual keyboard
        self.container = KeyboardWidget(layout_editor)
        self.container.clicked.connect(self.on_key_clicked)
        self.container.deselected.connect(self.on_key_deselected)

        row = QHBoxLayout()
        row.addLayout(layer_column)
        row.addStretch()
        row.addWidget(self.container)
        row.setAlignment(self.container, Qt.AlignHCenter | Qt.AlignTop)
        row.addStretch()
        row.addLayout(size_column)

        layout = QVBoxLayout()
        layout.addLayout(row)
        w = ClickableWidget()
        w.setLayout(layout)
        w.clicked.connect(self.on_empty_space_clicked)
        self.keyboard_area = w
        self.row = row
        self.layer_column = layer_column
        self.size_column = size_column
        # the keyboard is scaled to the space the top pane gives it (until +/- is used)
        self.auto_fit = True
        self.container.fit_mode = True
        w.resized.connect(self.fit_keyboard)
        w.resized.connect(self.update_picker_wrap)

        self.layer_buttons = []
        self.keyboard = None
        self.current_layer = 0

        layout_editor.changed.connect(self.on_layout_changed)

        self.container.anykey.connect(self.on_any_keycode)

        self.tabbed_keycodes = TabbedKeycodes()
        self.tabbed_keycodes.keycode_changed.connect(self.on_keycode_changed)
        self.tabbed_keycodes.anykey.connect(self.on_any_keycode)

        self.splitter = RatioSplitter(SPLIT_RATIO)
        self.splitter.addWidget(w)
        self.splitter.addWidget(self.tabbed_keycodes)
        self.splitter.setStretchFactor(0, SPLIT_RATIO[0])
        self.splitter.setStretchFactor(1, SPLIT_RATIO[1])
        self.addWidget(self.splitter)

        self.device = None
        KeycodeDisplay.notify_keymap_override(self)

    def on_empty_space_clicked(self):
        self.container.deselect()
        self.container.update()

    def on_keycode_changed(self, code):
        self.set_key(code)

    def rebuild_layers(self):
        # delete old layer labels
        for label in self.layer_buttons:
            label.hide()
            label.deleteLater()
        self.layer_buttons = []

        # create new layer labels
        for x in range(self.keyboard.layers):
            btn = SquareButton(str(x))
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(2.2)
            btn.setWidthFactor(3)   # wide layer buttons
            btn.setCheckable(True)
            btn.clicked.connect(lambda state, idx=x: self.switch_layer(idx))
            self.layout_layers.addWidget(btn)
            self.layer_buttons.append(btn)
        for x in range(0,2):
            btn = SquareButton("-") if x else SquareButton("+")
            btn.setFocusPolicy(Qt.NoFocus)
            btn.setRelSize(2.2)
            btn.setCheckable(False)
            btn.clicked.connect(lambda state, idx=x: self.adjust_size(idx))
            self.layout_size.addWidget(btn)
            self.layer_buttons.append(btn)

    def keyboard_space(self):
        """(width, height) the top pane leaves for the keyboard between the layer and zoom columns"""
        # (not layout().contentsRect(): that is invalid until the layout has been activated once)
        inner = self.keyboard_area.rect().marginsRemoved(self.keyboard_area.layout().contentsMargins())
        width = inner.width() - self.layer_column.sizeHint().width() - self.size_column.sizeHint().width() \
            - 2 * self.row.spacing()
        return width, inner.height()

    def update_picker_wrap(self):
        """Picker wrap width from the window's aspect: landscape windows wrap the picker at a width equal to
        the window height (block centred, contents left-aligned), portrait windows use the full width (§4.5)"""
        win = self.keyboard_area.window()
        width, height = win.width(), win.height()
        self.tabbed_keycodes.set_wrap_width(None if height > width else height)

    def fit_keyboard(self):
        """Auto-fit: the largest scale that shows the whole keyboard in the top pane"""
        if not self.auto_fit or not self.container.widgets:
            return
        scale = self.container.fit_scale(*self.keyboard_space(), max_scale=MAX_FIT_SCALE)
        if scale is not None and abs(scale - self.container.get_scale()) > 0.001:
            self.container.set_scale(scale)
            self.container.update_layout()

    def adjust_size(self, minus):
        # manual zoom: stop auto-fitting until the next keyboard is loaded
        self.auto_fit = False
        self.container.fit_mode = False
        if minus:
            self.container.set_scale(self.container.get_scale() - 0.1)
        else:
            self.container.set_scale(self.container.get_scale() + 0.1)
        self.refresh_layer_display()

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard

            # get number of layers
            self.rebuild_layers()

            self.container.set_keys(self.keyboard.keys, self.keyboard.encoders)
            self.auto_fit = True
            self.container.fit_mode = True
            self.fit_keyboard()
            self.update_picker_wrap()

            self.current_layer = 0
            self.on_layout_changed()

            self.tabbed_keycodes.recreate_keycode_buttons()
            TabbedKeycodes.tray.recreate_keycode_buttons()
            self.refresh_layer_display()
        self.container.setEnabled(self.valid())

    def valid(self):
        return isinstance(self.device, VialKeyboard)

    def save_layout(self):
        return self.keyboard.save_layout()

    def restore_layout(self, data):
        if json.loads(data.decode("utf-8")).get("uid") != self.keyboard.keyboard_id:
            ret = QMessageBox.question(self.widget(), "",
                                       tr("KeymapEditor", "Saved keymap belongs to a different keyboard,"
                                                          " are you sure you want to continue?"),
                                       QMessageBox.Yes | QMessageBox.No)
            if ret != QMessageBox.Yes:
                return
        self.keyboard.restore_layout(data)
        self.refresh_layer_display()

    def on_any_keycode(self):
        if self.container.active_key is None:
            return
        current_code = self.code_for_widget(self.container.active_key)
        if self.container.active_mask:
            kc = Keycode.find_inner_keycode(current_code)
            current_code = kc.qmk_id

        self.dlg = AnyKeycodeDialog(current_code)
        self.dlg.finished.connect(self.on_dlg_finished)
        self.dlg.setModal(True)
        self.dlg.show()

    def on_dlg_finished(self, res):
        if res > 0:
            self.on_keycode_changed(self.dlg.value)

    def code_for_widget(self, widget):
        if widget.desc.row is not None:
            return self.keyboard.layout[(self.current_layer, widget.desc.row, widget.desc.col)]
        else:
            return self.keyboard.encoder_layout[(self.current_layer, widget.desc.encoder_idx,
                                                 widget.desc.encoder_dir)]

    def refresh_layer_display(self):
        """ Refresh text on key widgets to display data corresponding to current layer """

        self.container.update_layout()

        for idx, btn in enumerate(self.layer_buttons):
            btn.setEnabled(idx != self.current_layer)
            btn.setChecked(idx == self.current_layer)

        for widget in self.container.widgets:
            code = self.code_for_widget(widget)
            KeycodeDisplay.display_keycode(widget, code)
        self.container.update()
        self.container.updateGeometry()

    def switch_layer(self, idx):
        self.container.deselect()
        self.current_layer = idx
        self.refresh_layer_display()

    def set_key(self, keycode):
        """ Change currently selected key to provided keycode """

        if self.container.active_key is None:
            return

        if isinstance(self.container.active_key, EncoderWidget):
            self.set_key_encoder(keycode)
        else:
            self.set_key_matrix(keycode)

        self.container.select_next()

    def set_key_encoder(self, keycode):
        l, i, d = self.current_layer, self.container.active_key.desc.encoder_idx,\
                            self.container.active_key.desc.encoder_dir

        # if masked, ensure that this is a byte-sized keycode
        if self.container.active_mask:
            if not Keycode.is_basic(keycode):
                return
            kc = Keycode.find_outer_keycode(self.keyboard.encoder_layout[(l, i, d)])
            if kc is None:
                return
            keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

        self.keyboard.set_encoder(l, i, d, keycode)
        self.refresh_layer_display()

    def set_key_matrix(self, keycode):
        l, r, c = self.current_layer, self.container.active_key.desc.row, self.container.active_key.desc.col

        if r >= 0 and c >= 0:
            # if masked, ensure that this is a byte-sized keycode
            if self.container.active_mask:
                if not Keycode.is_basic(keycode):
                    return
                kc = Keycode.find_outer_keycode(self.keyboard.layout[(l, r, c)])
                if kc is None:
                    return
                keycode = kc.qmk_id.replace("(kc)", "({})".format(keycode))

            self.keyboard.set_key(l, r, c, keycode)
            self.refresh_layer_display()

    def on_key_clicked(self):
        """ Called when a key on the keyboard widget is clicked """
        self.refresh_layer_display()
        if self.container.active_mask:
            self.tabbed_keycodes.set_keycode_filter(keycode_filter_masked)
        else:
            self.tabbed_keycodes.set_keycode_filter(None)

    def on_key_deselected(self):
        self.tabbed_keycodes.set_keycode_filter(None)

    def on_layout_changed(self):
        if self.keyboard is None:
            return

        self.refresh_layer_display()
        self.keyboard.set_layout_options(self.layout_editor.pack())

    def on_keymap_override(self):
        self.refresh_layer_display()
