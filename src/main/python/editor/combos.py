# SPDX-License-Identifier: GPL-2.0-or-later
from PyQt5 import QtCore
from PyQt5.QtCore import pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QSizePolicy, QGridLayout, QVBoxLayout, QLabel

from protocol.constants import VIAL_PROTOCOL_DYNAMIC
from widgets.key_widget import KeyWidget
from vial_device import VialKeyboard
from editor.basic_editor import BasicEditor
from widgets.entry_card import EntryCard, EntryCardContainer
from util import tr

# キーの描画倍率。カード内では通常より小さく描いて行間を詰める
CARD_KEY_SCALE = 0.7


class ComboEntryUI(QObject):

    key_changed = pyqtSignal()

    def __init__(self, idx):
        super().__init__()

        self.idx = idx
        self.container = QGridLayout()
        self.kc_inputs = []
        self.populate_container()

        w = QWidget()
        w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        w.setLayout(self.container)
        l = QVBoxLayout()
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(w)
        l.setAlignment(w, QtCore.Qt.AlignHCenter)
        self.w2 = QWidget()
        self.w2.setLayout(l)

    def populate_container(self):
        self.container.setVerticalSpacing(3)
        for x in range(4):
            kc_widget = KeyWidget()
            kc_widget.set_scale(CARD_KEY_SCALE)
            kc_widget.changed.connect(self.on_key_changed)
            self.container.addWidget(QLabel(tr("Combos", "Key {}").format(x + 1)), x, 0)
            self.container.addWidget(kc_widget, x, 1)
            self.kc_inputs.append(kc_widget)

        self.kc_output = KeyWidget()
        self.kc_output.set_scale(CARD_KEY_SCALE)
        self.kc_output.changed.connect(self.on_key_changed)
        self.container.addWidget(QLabel(tr("Combos", "Output key")), 4, 0)
        self.container.addWidget(self.kc_output, 4, 1)

    def widget(self):
        return self.w2

    def load(self, data):
        objs = self.kc_inputs + [self.kc_output]
        for o in objs:
            o.blockSignals(True)

        for x in range(4):
            self.kc_inputs[x].set_keycode(data[x])
        self.kc_output.set_keycode(data[4])

        for o in objs:
            o.blockSignals(False)

    def save(self):
        return (
            self.kc_inputs[0].keycode,
            self.kc_inputs[1].keycode,
            self.kc_inputs[2].keycode,
            self.kc_inputs[3].keycode,
            self.kc_output.keycode
        )

    def on_key_changed(self):
        self.key_changed.emit()


class Combos(BasicEditor):

    def __init__(self):
        super().__init__()
        self.keyboard = None

        self.combo_entries = []
        self.combo_entries_available = []
        self.cards_available = []
        self.cards = []
        self.container = EntryCardContainer()
        for x in range(128):
            entry = ComboEntryUI(x)
            entry.key_changed.connect(self.on_key_changed)
            self.combo_entries_available.append(entry)
            card = EntryCard(entry.widget())
            card.set_title(tr("Combos", "Combo {}").format(x + 1))
            self.cards_available.append(card)

        self.addWidget(self.container)

    def rebuild_ui(self):
        self.combo_entries = self.combo_entries_available[:self.keyboard.combo_count]
        self.cards = self.cards_available[:self.keyboard.combo_count]
        self.container.set_cards(self.cards)
        for x, e in enumerate(self.combo_entries):
            e.load(self.keyboard.combo_get(x))

    def rebuild(self, device):
        super().rebuild(device)
        if self.valid():
            self.keyboard = device.keyboard
            self.rebuild_ui()

    def valid(self):
        return isinstance(self.device, VialKeyboard) and \
               (self.device.keyboard and self.device.keyboard.vial_protocol >= VIAL_PROTOCOL_DYNAMIC
                and self.device.keyboard.combo_count > 0)

    def on_key_changed(self):
        for x, e in enumerate(self.combo_entries):
            self.keyboard.combo_set(x, self.combo_entries[x].save())
